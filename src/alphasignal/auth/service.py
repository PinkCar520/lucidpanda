from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.alphasignal.auth.models import User, RefreshToken, AuthAuditLog
from src.alphasignal.auth.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from src.alphasignal.config import settings

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, email: str, password: str, full_name: str = None) -> User:
        hashed_password = get_password_hash(password)
        db_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create_session(self, user_id: str, device_name: str = None, ip_address: str = None) -> Tuple[str, str]:
        # Create Tokens
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        # Save Refresh Token Hash
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db_refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(refresh_token),
            device_name=device_name,
            ip_address=ip_address,
            expires_at=expires_at
        )
        self.db.add(db_refresh_token)
        
        # Log Audit
        self.log_audit(user_id, "LOGIN", ip_address, details={"device": device_name})
        
        self.db.commit()
        return access_token, refresh_token

    def refresh_session(self, refresh_token: str, ip_address: str = None) -> Optional[Tuple[str, str]]:
        token_hash = self._hash_token(refresh_token)
        db_token = self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at == None,
                RefreshToken.expires_at > datetime.utcnow()
            )
        ).first()

        if not db_token:
            return None

        # Create new tokens
        user_id = str(db_token.user_id)
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)
        
        # Rotation: Revoke old, save new
        db_token.revoked_at = datetime.utcnow()
        db_token.replaced_by_token_hash = self._hash_token(new_refresh_token)
        
        new_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_db_token = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(new_refresh_token),
            device_name=db_token.device_name,
            ip_address=ip_address,
            expires_at=new_expires_at
        )
        self.db.add(new_db_token)
        
        self.db.commit()
        return new_access_token, new_refresh_token

    def log_audit(self, user_id: str, action: str, ip_address: str = None, user_agent: str = None, details: dict = None):
        log = AuthAuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        self.db.add(log)
        # We don't commit here, assume it's part of a larger transaction or committed separately
