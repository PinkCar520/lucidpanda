from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Date, Uuid
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100))  # Renamed from full_name
    avatar_url = Column(String(255), nullable=True)
    nickname = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    birthday = Column(Date, nullable=True)
    location = Column(String(255), nullable=True)
    language_preference = Column(String(10), default='en')
    timezone = Column(String(50), default='UTC')
    theme_preference = Column(String(20), default='system')
    phone_number = Column(String(20), unique=True, nullable=True)
    is_phone_verified = Column(Boolean, default=False)
    two_fa_secret = Column(String(255), nullable=True)
    is_two_fa_enabled = Column(Boolean, default=False)
    
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    notification_preferences = relationship("UserNotificationPreference", uselist=False, back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    audit_logs = relationship("AuthAuditLog", back_populates="user")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmailChangeRequest(Base):
    __tablename__ = "email_change_requests"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    old_email = Column(String(255), nullable=False)
    new_email = Column(String(255), nullable=False)
    old_email_token_hash = Column(String(255), unique=True, nullable=True)
    new_email_token_hash = Column(String(255), unique=True, nullable=True)
    old_email_verified_at = Column(DateTime(timezone=True), nullable=True)
    new_email_verified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_completed = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(String(255), nullable=False, index=True)
    # device_name replaced by device_info
    device_info = Column(JSON, nullable=True)
    ip_address = Column(String(45)) # Supports IPv6
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True))
    replaced_by_token_hash = Column(String(255))
    
    user = relationship("User", back_populates="refresh_tokens")

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at > func.now()

class AuthAuditLog(Base):
    __tablename__ = "auth_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")

class PhoneVerificationToken(Base):
    __tablename__ = "phone_verification_tokens"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    phone_number = Column(String(20), nullable=False)
    otp_code_hash = Column(String(255), nullable=False)
    purpose = Column(String(50), nullable=False) # e.g., 'BIND_PHONE', '2FA_SMS'
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    app_push_enabled = Column(Boolean, default=False)
    email_frequency = Column(String(20), default='daily')
    sms_frequency = Column(String(20), default='immediate')
    subscribed_types = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="notification_preferences")

class InSiteMessage(Base):
    __tablename__ = "in_site_messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender_type = Column(String(50), default='system')
    subject = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    public_key = Column(String(255), unique=True, nullable=False)
    secret_hash = Column(String(255), nullable=False)
    permissions = Column(JSON, nullable=False)
    ip_whitelist = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("APIKeyUsageLog", back_populates="api_key")

class APIKeyUsageLog(Base):
    __tablename__ = "api_key_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Uuid(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String(255), nullable=False)
    http_method = Column(String(10), nullable=False)
    ip_address = Column(String(45), nullable=True)
    status_code = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    api_key = relationship("APIKey", back_populates="usage_logs")
