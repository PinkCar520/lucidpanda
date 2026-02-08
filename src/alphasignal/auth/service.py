from datetime import datetime, timedelta, date
from typing import Optional, Tuple, List, Union
import hashlib
import random
import string
import pyotp
import qrcode
import io
import base64
import secrets
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, text
from src.alphasignal.auth.models import User, RefreshToken, AuthAuditLog, PasswordResetToken, EmailChangeRequest, PhoneVerificationToken, UserNotificationPreference, InSiteMessage, APIKey, APIKeyUsageLog
from src.alphasignal.auth.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from src.alphasignal.config import settings
from src.alphasignal.utils.email import send_email

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def _to_uuid(self, id_val: Union[str, uuid.UUID]) -> uuid.UUID:
        if isinstance(id_val, str):
            return uuid.UUID(id_val)
        return id_val

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, email: str, password: str, full_name: str = None) -> User:
        hashed_password = get_password_hash(password)
        db_user = User(
            email=email,
            hashed_password=hashed_password,
            name=full_name
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
        user_uuid = self._to_uuid(user_id)
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db_refresh_token = RefreshToken(
            user_id=user_uuid,
            token_hash=self._hash_token(refresh_token),
            device_info={"name": device_name} if device_name else None,
            ip_address=ip_address,
            expires_at=expires_at
        )
        self.db.add(db_refresh_token)
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

        user_id = str(db_token.user_id)
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)
        
        db_token.revoked_at = datetime.utcnow()
        db_token.replaced_by_token_hash = self._hash_token(new_refresh_token)
        
        new_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_db_token = RefreshToken(
            user_id=db_token.user_id,
            token_hash=self._hash_token(new_refresh_token),
            device_info=db_token.device_info,
            ip_address=ip_address,
            expires_at=new_expires_at
        )
        self.db.add(new_db_token)
        self.db.commit()
        return new_access_token, new_refresh_token

    def update_user(self, user_id: str, 
                    name: Optional[str] = None,
                    nickname: Optional[str] = None,
                    gender: Optional[str] = None,
                    birthday: Optional[date] = None,
                    location: Optional[str] = None,
                    language_preference: Optional[str] = None,
                    timezone: Optional[str] = None,
                    theme_preference: Optional[str] = None
                    ) -> Optional[User]:
        
        user_uuid = self._to_uuid(user_id)
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return None
        
        if name is not None: user.name = name
        if nickname is not None: user.nickname = nickname
        if gender is not None: user.gender = gender
        if birthday is not None: user.birthday = birthday
        if location is not None: user.location = location
        if language_preference is not None: user.language_preference = language_preference
        if timezone is not None: user.timezone = timezone
        if theme_preference is not None: user.theme_preference = theme_preference
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_avatar(self, user_id: str, avatar_url: str) -> Optional[User]:
        user_uuid = self._to_uuid(user_id)
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return None
        user.avatar_url = avatar_url
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user_id: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        user_uuid = self._to_uuid(user_id)
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return False, "User not found"
        if not verify_password(current_password, user.hashed_password):
            return False, "Incorrect current password"
        
        user.hashed_password = get_password_hash(new_password)
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user_uuid).update({
            "revoked_at": datetime.utcnow()
        })
        self.db.add(user)
        self.db.commit()
        
        email_body = f"<p>Hello {user.name or user.email},</p><p>Your password was recently changed.</p>"
        send_email(to_email=user.email, subject="AlphaSignal Password Changed", body=email_body)
        return True, "Password changed successfully"

    def initiate_email_change(self, user_id: str, current_password: str, new_email: str) -> Tuple[bool, str]:
        user_uuid = self._to_uuid(user_id)
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if not user or not verify_password(current_password, user.hashed_password):
            return False, "Invalid credentials"
        if self.get_user_by_email(new_email):
            return False, "Email already in use"
        
        self.db.query(EmailChangeRequest).filter(EmailChangeRequest.user_id == user_uuid).delete()
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        db_request = EmailChangeRequest(
            user_id=user_uuid,
            new_email=new_email,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=60)
        )
        self.db.add(db_request)
        self.db.commit()
        
        verify_link = f"{settings.FRONTEND_BASE_URL}/en/settings/security/verify-email?token={raw_token}"
        send_email(to_email=new_email, subject="Verify your new email address", body=f"<p>Verify: <a href='{verify_link}'>Link</a></p>")
        return True, "Verification email sent"

    def verify_email_change(self, raw_token: str) -> Tuple[bool, str]:
        token_hash = self._hash_token(raw_token)
        db_request = self.db.query(EmailChangeRequest).filter(
            and_(EmailChangeRequest.token_hash == token_hash, EmailChangeRequest.expires_at > datetime.utcnow())
        ).first()
        if not db_request: return False, "Invalid or expired token"
        
        user = self.db.query(User).filter(User.id == db_request.user_id).first()
        if not user: return False, "User not found"
        
        user.email = db_request.new_email
        user.is_verified = True
        self.db.add(user)
        self.db.delete(db_request)
        self.db.commit()
        return True, "Email updated successfully"

    def request_phone_verification(self, user_id: str, phone_number: str, purpose: str = 'BIND_PHONE') -> Tuple[bool, str]:
        user_uuid = self._to_uuid(user_id)
        code = ''.join(random.choices(string.digits, k=6))
        code_hash = self._hash_token(code)
        db_token = PhoneVerificationToken(
            user_id=user_uuid,
            phone_number=phone_number,
            otp_code_hash=code_hash,
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        self.db.add(db_token)
        self.db.commit()
        print(f"MOCK SMS to {phone_number}: Your code is {code}")
        return True, "Verification code sent"

    def verify_phone_binding(self, user_id: str, phone_number: str, code: str) -> Tuple[bool, str]:
        user_uuid = self._to_uuid(user_id)
        code_hash = self._hash_token(code)
        db_token = self.db.query(PhoneVerificationToken).filter(
            and_(
                PhoneVerificationToken.user_id == user_uuid,
                PhoneVerificationToken.phone_number == phone_number,
                PhoneVerificationToken.otp_code_hash == code_hash,
                PhoneVerificationToken.is_used == False,
                PhoneVerificationToken.expires_at > datetime.utcnow()
            )
        ).first()
        if not db_token: return False, "Invalid or expired code"
        
        db_token.is_used = True
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if user:
            user.phone_number = phone_number
            user.is_phone_verified = True
            self.db.add(user)
        self.db.commit()
        return True, "Phone bound successfully"

    def unbind_phone(self, user_id: str) -> bool:
        user_uuid = self._to_uuid(user_id)
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if user:
            user.phone_number = None
            user.is_phone_verified = False
            self.db.add(user)
            self.db.commit()
            return True
        return False

    def setup_2fa(self, user_id: str) -> Tuple[str, str]:
        user_uuid = self._to_uuid(user_id)
        secret = pyotp.random_base32()
        user = self.db.query(User).filter(User.id == user_uuid).first()
        provision_url = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="AlphaSignal")
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provision_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return secret, f"data:image/png;base64,{qr_base64}"

    def verify_and_enable_2fa(self, user_id: str, secret: str, code: str) -> Tuple[bool, str]:
        user_uuid = self._to_uuid(user_id)
        if pyotp.TOTP(secret).verify(code):
            user = self.db.query(User).filter(User.id == user_uuid).first()
            if user:
                user.two_fa_secret = secret
                user.is_two_fa_enabled = True
                self.db.commit()
                return True, "2FA enabled"
        return False, "Invalid code"

    def disable_2fa(self, user_id: str) -> bool:
        user_uuid = self._to_uuid(user_id)
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if user:
            user.two_fa_secret = None
            user.is_two_fa_enabled = False
            self.db.commit()
            return True
        return False

    def get_notification_preferences(self, user_id: str) -> UserNotificationPreference:
        user_uuid = self._to_uuid(user_id)
        prefs = self.db.query(UserNotificationPreference).filter(UserNotificationPreference.user_id == user_uuid).first()
        if not prefs:
            prefs = UserNotificationPreference(user_id=user_uuid)
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)
        return prefs

    def update_notification_preferences(self, user_id: str, **kwargs) -> UserNotificationPreference:
        prefs = self.get_notification_preferences(user_id)
        for key, value in kwargs.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)
        self.db.commit()
        self.db.refresh(prefs)
        return prefs

    def get_in_site_messages(self, user_id: str, limit: int = 50) -> List[InSiteMessage]:
        user_uuid = self._to_uuid(user_id)
        return self.db.query(InSiteMessage).filter(InSiteMessage.recipient_user_id == user_uuid).order_by(desc(InSiteMessage.sent_at)).limit(limit).all()

    def mark_message_as_read(self, user_id: str, message_id: str) -> bool:
        user_uuid = self._to_uuid(user_id)
        message_uuid = self._to_uuid(message_id)
        msg = self.db.query(InSiteMessage).filter(and_(InSiteMessage.id == message_uuid, InSiteMessage.recipient_user_id == user_uuid)).first()
        if msg:
            msg.is_read = True
            msg.read_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def create_in_site_message(self, user_id: str, subject: str, content: str, sender_type: str = 'system', message_type: str = 'notification'):
        user_uuid = self._to_uuid(user_id)
        msg = InSiteMessage(
            recipient_user_id=user_uuid,
            subject=subject,
            content=content,
            sender_type=sender_type,
            message_type=message_type
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def generate_api_key(self, user_id: str, name: str, permissions: List[str], ip_whitelist: List[str] = None, expires_at: datetime = None) -> Tuple[APIKey, str]:
        user_uuid = self._to_uuid(user_id)
        public_key = secrets.token_hex(16)
        secret = secrets.token_urlsafe(32)
        secret_hash = self._hash_token(secret)
        
        api_key = APIKey(
            user_id=user_uuid,
            name=name,
            public_key=public_key,
            secret_hash=secret_hash,
            permissions=permissions,
            ip_whitelist=ip_whitelist,
            expires_at=expires_at
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key, secret

    def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        user_uuid = self._to_uuid(user_id)
        return self.db.query(APIKey).filter(APIKey.user_id == user_uuid).order_by(desc(APIKey.created_at)).all()

    def update_api_key(self, user_id: str, key_id: str, **kwargs) -> Optional[APIKey]:
        user_uuid = self._to_uuid(user_id)
        key_uuid = self._to_uuid(key_id)
        key = self.db.query(APIKey).filter(and_(APIKey.id == key_uuid, APIKey.user_id == user_uuid)).first()
        if not key: return None
        for k, v in kwargs.items():
            if hasattr(key, k) and v is not None:
                setattr(key, k, v)
        self.db.commit()
        self.db.refresh(key)
        return key

    def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        user_uuid = self._to_uuid(user_id)
        key_uuid = self._to_uuid(key_id)
        key = self.db.query(APIKey).filter(and_(APIKey.id == key_uuid, APIKey.user_id == user_uuid)).first()
        if key:
            self.db.delete(key)
            self.db.commit()
            return True
        return False

    def log_api_key_usage(self, api_key_id: str, endpoint: str, http_method: str, ip_address: str, status_code: int = None, details: dict = None):
        key_uuid = self._to_uuid(api_key_id)
        log = APIKeyUsageLog(
            api_key_id=key_uuid,
            endpoint=endpoint,
            http_method=http_method,
            ip_address=ip_address,
            status_code=status_code,
            details=details
        )
        self.db.add(log)
        self.db.commit()

    def get_asset_overview(self, user_id: str):
        user_uuid = self._to_uuid(user_id)
        watchlist_count = self.db.execute(text("SELECT COUNT(*) FROM fund_watchlist WHERE user_id = :uid"), {"uid": str(user_uuid)}).scalar() or 0
        
        return {
            "total_assets": 125430.50,
            "available_funds": 85200.00,
            "frozen_funds": 40230.50,
            "pnl_today": 1240.25,
            "pnl_percentage": 0.98,
            "active_strategies": 3,
            "watchlist_count": watchlist_count
        }

    def get_active_sessions(self, user_id: str) -> List[RefreshToken]:
        user_uuid = self._to_uuid(user_id)
        return self.db.query(RefreshToken).filter(
            and_(RefreshToken.user_id == user_uuid, RefreshToken.revoked_at == None, RefreshToken.expires_at > datetime.utcnow())
        ).all()

    def revoke_session(self, user_id: str, session_id: int) -> bool:
        user_uuid = self._to_uuid(user_id)
        token = self.db.query(RefreshToken).filter(and_(RefreshToken.id == session_id, RefreshToken.user_id == user_uuid)).first()
        if token:
            token.revoked_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def log_audit(self, user_id: str, action: str, ip_address: str = None, user_agent: str = None, details: dict = None):
        user_uuid = self._to_uuid(user_id) if user_id else None
        log = AuthAuditLog(user_id=user_uuid, action=action, ip_address=ip_address, user_agent=user_agent, details=details)
        self.db.add(log)

    def get_audit_logs(self, user_id: str, limit: int = 50) -> List[AuthAuditLog]:
        user_uuid = self._to_uuid(user_id)
        return self.db.query(AuthAuditLog).filter(AuthAuditLog.user_id == user_uuid).order_by(desc(AuthAuditLog.created_at)).limit(limit).all()

    def generate_password_reset_token(self, email: str) -> Optional[str]:
        user = self.get_user_by_email(email)
        if not user: return None
        self.db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        db_token = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=datetime.utcnow() + timedelta(minutes=60))
        self.db.add(db_token)
        self.db.commit()
        return raw_token

    def reset_password(self, raw_token: str, new_password: str) -> bool:
        token_hash = self._hash_token(raw_token)
        db_token = self.db.query(PasswordResetToken).filter(and_(PasswordResetToken.token_hash == token_hash, PasswordResetToken.expires_at > datetime.utcnow())).first()
        if not db_token: return False
        user = self.db.query(User).filter(User.id == db_token.user_id).first()
        if not user: return False
        user.hashed_password = get_password_hash(new_password)
        self.db.delete(db_token)
        self.db.commit()
        return True
