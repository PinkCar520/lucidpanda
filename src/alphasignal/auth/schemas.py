from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None # Changed from full_name to name to match model
    full_name: Optional[str] = None # Keep for backward compatibility if needed, or deprecate

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserOut(UserBase):
    id: UUID
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    # New fields
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[date] = None
    location: Optional[str] = None
    language_preference: Optional[str] = "en"
    timezone: Optional[str] = "UTC"
    theme_preference: Optional[str] = "system"
    phone_number: Optional[str] = None
    is_phone_verified: bool = False
    is_two_fa_enabled: bool = False

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut # Add user information to the token response

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class MessageResponse(BaseModel):
    message: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[date] = None
    location: Optional[str] = None
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    theme_preference: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class EmailChangeInitiateRequest(BaseModel):
    new_email: EmailStr
    current_password: str

class EmailChangeVerifyRequest(BaseModel):
    token: str

class AvatarUploadResponse(BaseModel):
    avatar_url: str

class SessionOut(BaseModel):
    id: int
    device_info: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None
    is_current: bool = False # Helper field

    class Config:
        from_attributes = True

class PhoneNumberPayload(BaseModel):
    phone_number: str

class PhoneVerificationPayload(BaseModel):
    phone_number: str
    code: str

class TwoFASetupResponse(BaseModel):
    secret: str
    qr_code_url: str

class TwoFAVerifyPayload(BaseModel):
    code: str
    secret: str

class NotificationPreferencesOut(BaseModel):
    email_enabled: bool
    sms_enabled: bool
    app_push_enabled: bool
    email_frequency: str
    sms_frequency: str
    subscribed_types: List[str]

    class Config:
        from_attributes = True

class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    app_push_enabled: Optional[bool] = None
    email_frequency: Optional[str] = None
    sms_frequency: Optional[str] = None
    subscribed_types: Optional[List[str]] = None

class InSiteMessageOut(BaseModel):
    id: UUID
    sender_type: str
    subject: str
    content: str
    message_type: Optional[str] = None
    is_read: bool
    sent_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str] = ["read_only"]
    expires_at: Optional[datetime] = None
    ip_whitelist: Optional[List[str]] = None

class APIKeyOut(BaseModel):
    id: UUID
    name: str
    public_key: str
    # secret: str - only returned on creation
    permissions: List[str]
    ip_whitelist: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class APIKeyCreateResponse(APIKeyOut):
    secret: str # Clear text secret only once

class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    ip_whitelist: Optional[List[str]] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class APIKeyUsageLogOut(BaseModel):
    endpoint: str
    http_method: str
    ip_address: Optional[str]
    status_code: Optional[int]
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLogOut(BaseModel):
    id: int
    action: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True

class AssetOverviewOut(BaseModel):
    total_assets: float
    available_funds: float
    frozen_funds: float
    pnl_today: float
    pnl_percentage: float
    active_strategies: int
    watchlist_count: int
