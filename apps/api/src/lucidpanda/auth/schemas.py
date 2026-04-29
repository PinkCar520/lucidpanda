from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str | None = Field(
        None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$"
    )
    name: str | None = None  # Changed from full_name to name to match model
    full_name: str | None = (
        None  # Keep for backward compatibility if needed, or deprecate
    )


class UserCreate(UserBase):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    username_updated_at: datetime | None = None

    # New fields
    avatar_url: str | None = None
    nickname: str | None = None
    gender: str | None = None
    birthday: date | None = None
    location: str | None = None
    language_preference: str | None = "en"
    timezone: str | None = "UTC"
    theme_preference: str | None = "system"
    phone_number: str | None = None
    is_phone_verified: bool = False
    is_two_fa_enabled: bool = False
    is_pro: bool = False
    pro_expires_at: datetime | None = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut  # Add user information to the token response


class TokenRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    message: str


class UserUpdate(BaseModel):
    name: str | None = None
    nickname: str | None = None
    gender: str | None = None
    birthday: date | None = None
    location: str | None = None
    language_preference: str | None = None
    timezone: str | None = None
    theme_preference: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class UsernameUpdate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")


class EmailChangeInitiateRequest(BaseModel):
    new_email: EmailStr
    current_password: str


class EmailChangeVerifyRequest(BaseModel):
    token: str


class AvatarUploadResponse(BaseModel):
    avatar_url: str


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_info: dict | None = None
    ip_address: str | None = None
    created_at: datetime
    last_active_at: datetime | None = None
    is_current: bool = False  # Helper field


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
    model_config = ConfigDict(from_attributes=True)

    email_enabled: bool
    sms_enabled: bool
    app_push_enabled: bool
    email_frequency: str
    sms_frequency: str
    subscribed_types: list[str]


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    app_push_enabled: bool | None = None
    email_frequency: str | None = None
    sms_frequency: str | None = None
    subscribed_types: list[str] | None = None


class InSiteMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_type: str
    subject: str
    content: str
    message_type: str | None = None
    is_read: bool
    sent_at: datetime
    read_at: datetime | None = None


class APIKeyCreate(BaseModel):
    name: str
    permissions: list[str] = ["read_only"]
    expires_at: datetime | None = None
    ip_whitelist: list[str] | None = None


class APIKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    public_key: str
    # secret: str - only returned on creation
    permissions: list[str]
    ip_whitelist: list[str] | None = None
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None


class APIKeyCreateResponse(APIKeyOut):
    secret: str  # Clear text secret only once


class APIKeyUpdate(BaseModel):
    name: str | None = None
    permissions: list[str] | None = None
    ip_whitelist: list[str] | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None


class APIKeyUsageLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    endpoint: str
    http_method: str
    ip_address: str | None
    status_code: int | None
    timestamp: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    ip_address: str | None
    user_agent: str | None
    details: dict | None
    created_at: datetime


class AssetOverviewOut(BaseModel):
    total_assets: float
    available_funds: float
    frozen_funds: float
    pnl_today: float
    pnl_percentage: float
    active_strategies: int
    watchlist_count: int


# WebAuthn Schemas


class PasskeyRegistrationVerify(BaseModel):
    registration_data: dict
    name: str | None = "My Device"


class PasskeyAuthenticationVerify(BaseModel):
    auth_data: dict
    state: str


class PasskeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    created_at: datetime
    last_used_at: datetime | None = None
    transports: list[str] | None = None
