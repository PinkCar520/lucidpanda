from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.alphasignal.auth.models import User, RefreshToken, AuthAuditLog, PasswordResetToken
from src.alphasignal.auth.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from src.alphasignal.config import settings
from src.alphasignal.utils.email import send_email # Import send_email

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
    
    def generate_password_reset_token(self, email: str) -> Optional[str]:
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        # Invalidate any existing tokens for this user
        self.db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()

        # Generate a new token
        from uuid import uuid4
        raw_token = str(uuid4())
        token_hash = self._hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        
        db_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.db.add(db_token)
        self.db.commit()
        
        # Send email with reset link (assuming frontend base URL)
        reset_link = f"{settings.FRONTEND_BASE_URL}/en/reset-password?token={raw_token}"
        email_body = f"""
            <p>Hello,</p>
            <p>You have requested to reset your password for AlphaSignal. Please click the link below to reset your password:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>This link is valid for {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
            <p>If you did not request a password reset, please ignore this email.</p>
            <p>Regards,<br>AlphaSignal Team</p>
        """
        send_email(to_email=user.email, subject="AlphaSignal Password Reset Request", body=email_body)
        
        return raw_token

    def reset_password(self, raw_token: str, new_password: str) -> bool:
        token_hash = self._hash_token(raw_token)
        db_token = self.db.query(PasswordResetToken).filter(
            and_(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.expires_at > datetime.utcnow()
            )
        ).first()

        if not db_token:
            return False
        
        user = self.db.query(User).filter(User.id == db_token.user_id).first()
        if not user:
            return False
        
        user.hashed_password = get_password_hash(new_password)
        self.db.add(user)
        self.db.delete(db_token) # Invalidate token after use
        self.db.commit()
        
        return True

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
