from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.alphasignal.auth.schemas import UserCreate, UserOut, Token, RefreshTokenRequest
from src.alphasignal.auth.service import AuthService
from src.alphasignal.auth.dependencies import get_db, get_current_user
from src.alphasignal.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    user = auth_service.get_user_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    return auth_service.create_user(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name
    )

@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        # Audit failed login
        auth_service.log_audit(None, "FAILED_LOGIN", request.client.host, details={"email": form_data.username})
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, refresh_token = auth_service.create_session(
        user_id=str(user.id),
        device_name=request.headers.get("user-agent"),
        ip_address=request.client.host
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    refresh_in: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    tokens = auth_service.refresh_session(refresh_in.refresh_token, ip_address=request.client.host)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    access_token, refresh_token = tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return current_user
