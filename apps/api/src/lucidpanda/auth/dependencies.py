from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlmodel import select

from src.lucidpanda.auth.models import User
from src.lucidpanda.auth.schemas import TokenPayload
from src.lucidpanda.auth.security import decode_token
from src.lucidpanda.config import settings

# Database Setup
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = str(payload.get("sub") or "")
        token_type: str = str(payload.get("type") or "")
        if user_id is None or token_type != "access":
            print(f"[AUTH] Invalid payload: user_id={user_id}, type={token_type}")
            raise credentials_exception
        token_data = TokenPayload(sub=user_id, type=token_type)
    except JWTError as e:
        print(f"[AUTH] JWT Decode Error: {e}")
        raise credentials_exception from e
    except Exception as e:
        print(f"[AUTH] Unexpected Error during decode: {e}")
        raise credentials_exception from e

    user = db.execute(select(User).where(User.id == token_data.sub)).scalars().first()
    if user is None:
        print(f"[AUTH] User not found: id={token_data.sub}")
        raise credentials_exception
    if not user.is_active:
        print(f"[AUTH] User inactive: id={token_data.sub}")
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_pro_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    from datetime import datetime, UTC
    if not current_user.is_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ERR_PRO_REQUIRED",
                "message": "此功能仅限 Pro 订阅用户使用"
            }
        )
    
    if current_user.pro_expires_at and current_user.pro_expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ERR_PRO_EXPIRED",
                "message": "您的 Pro 订阅已过期"
            }
        )
        
    return current_user
