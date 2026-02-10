from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.alphasignal.auth.schemas import (
    UserCreate, UserOut, Token, RefreshTokenRequest, 
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
    UserUpdate, UsernameUpdate, PasswordChangeRequest, EmailChangeInitiateRequest, EmailChangeVerifyRequest,
    AvatarUploadResponse, SessionOut, PhoneNumberPayload, PhoneVerificationPayload,
    TwoFASetupResponse, TwoFAVerifyPayload, NotificationPreferencesOut, NotificationPreferencesUpdate,
    InSiteMessageOut, APIKeyCreate, APIKeyOut, APIKeyUpdate, APIKeyCreateResponse,
    AssetOverviewOut, AuditLogOut
)
from src.alphasignal.auth.service import AuthService
from src.alphasignal.auth.dependencies import get_db, get_current_user
from src.alphasignal.config import settings
from typing import List
import os
import uuid
import shutil

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.patch("/me/username", response_model=MessageResponse)
def update_username(
    body: UsernameUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    success, message = auth_service.update_username(str(current_user.id), body.username)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.get("/audit-log", response_model=List[AuditLogOut])
def get_audit_log(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    return auth_service.get_audit_logs(str(current_user.id), limit=limit)

@router.get("/assets/me/overview", response_model=AssetOverviewOut)
def get_asset_overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    return auth_service.get_asset_overview(str(current_user.id))

@router.get("/api-keys/me", response_model=List[APIKeyOut])
def get_api_keys(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    return auth_service.get_user_api_keys(str(current_user.id))

@router.post("/api-keys/me", response_model=APIKeyCreateResponse)
def create_api_key(
    body: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    api_key, secret = auth_service.generate_api_key(
        str(current_user.id), 
        body.name, 
        body.permissions, 
        body.ip_whitelist, 
        body.expires_at
    )
    return {**api_key.__dict__, "secret": secret}

@router.put("/api-keys/me/{key_id}", response_model=APIKeyOut)
def update_api_key(
    key_id: str,
    body: APIKeyUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    key = auth_service.update_api_key(str(current_user.id), key_id, **body.dict(exclude_unset=True))
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    return key

@router.delete("/api-keys/me/{key_id}", response_model=MessageResponse)
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    if auth_service.revoke_api_key(str(current_user.id), key_id):
        return {"message": "API Key revoked successfully"}
    raise HTTPException(status_code=404, detail="API Key not found")

@router.get("/notifications/me/inbox", response_model=List[InSiteMessageOut])
def get_inbox(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    return auth_service.get_in_site_messages(str(current_user.id), limit=limit)

@router.put("/notifications/me/inbox/{message_id}/read", response_model=MessageResponse)
def mark_message_read(
    message_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    if auth_service.mark_message_as_read(str(current_user.id), message_id):
        return {"message": "Message marked as read"}
    raise HTTPException(status_code=404, detail="Message not found")

@router.get("/notifications/me/preferences", response_model=NotificationPreferencesOut)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    return auth_service.get_notification_preferences(str(current_user.id))

@router.put("/notifications/me/preferences", response_model=NotificationPreferencesOut)
def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    return auth_service.update_notification_preferences(str(current_user.id), **body.dict(exclude_unset=True))

@router.post("/2fa/setup", response_model=TwoFASetupResponse)
def setup_2fa(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    secret, qr_url = auth_service.setup_2fa(str(current_user.id))
    return {"secret": secret, "qr_code_url": qr_url}

@router.post("/2fa/verify", response_model=MessageResponse)
def verify_2fa(
    body: TwoFAVerifyPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    success, message = auth_service.verify_and_enable_2fa(str(current_user.id), body.secret, body.code)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.delete("/2fa", response_model=MessageResponse)
def disable_2fa(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    if auth_service.disable_2fa(str(current_user.id)):
        return {"message": "2FA disabled successfully"}
    raise HTTPException(status_code=400, detail="Failed to disable 2FA")

@router.post("/phone/request-verification", response_model=MessageResponse)
def request_phone_verification(
    body: PhoneNumberPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    success, message = auth_service.request_phone_verification(str(current_user.id), body.phone_number)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/phone/verify-binding", response_model=MessageResponse)
def verify_phone_binding(
    body: PhoneVerificationPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    success, message = auth_service.verify_phone_binding(str(current_user.id), body.phone_number, body.code)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.delete("/phone", response_model=MessageResponse)
def unbind_phone(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    if auth_service.unbind_phone(str(current_user.id)):
        return {"message": "Phone number unbound successfully"}
    raise HTTPException(status_code=400, detail="Failed to unbind phone")

@router.get("/sessions", response_model=List[SessionOut])
def get_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    sessions = auth_service.get_active_sessions(str(current_user.id))
    return sessions

@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def revoke_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    success = auth_service.revoke_session(str(current_user.id), session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session revoked successfully"}

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    
    if auth_service.get_user_by_email(user_in.email):
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
        
    if auth_service.get_user_by_username(user_in.username):
        raise HTTPException(
            status_code=400,
            detail="This username is already taken.",
        )

    return auth_service.create_user(
        email=user_in.email,
        username=user_in.username,
        password=user_in.password,
        full_name=user_in.name or user_in.full_name
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
        auth_service.log_audit(None, "FAILED_LOGIN", request.client.host, details={"identifier": form_data.username})
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect identifier or password",
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
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
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

@router.patch("/me", response_model=UserOut)
def update_profile(
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    user = auth_service.update_user(
        str(current_user.id), 
        name=body.name,
        nickname=body.nickname,
        gender=body.gender,
        birthday=body.birthday,
        location=body.location,
        language_preference=body.language_preference,
        timezone=body.timezone,
        theme_preference=body.theme_preference
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, and WebP are allowed.")
    
    from PIL import Image
    import io

    upload_dir = os.path.join(settings.BASE_DIR, "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Use .webp extension for optimized storage
    filename = f"{current_user.id}_{uuid.uuid4()}.webp"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        # Read the uploaded file into memory
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if necessary (e.g. for RGBA PNGs to WebP)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        # Resize using Lanczos for high quality
        # Standard profile size 256x256 is plenty for UI display
        image.thumbnail((256, 256), Image.Resampling.LANCZOS)
        
        # Save as WebP with optimized quality
        image.save(file_path, "WEBP", quality=85, optimize=True)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not process image: {str(e)}")
        
    avatar_url = f"/static/avatars/{filename}" 
    auth_service = AuthService(db)
    auth_service.update_avatar(str(current_user.id), avatar_url)
    
    return {"avatar_url": avatar_url}

@router.post("/password/change", response_model=MessageResponse)
def change_password(
    body: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    success, message = auth_service.change_password(
        str(current_user.id), 
        body.current_password, 
        body.new_password
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/email/change-request", response_model=MessageResponse)
def initiate_email_change(
    body: EmailChangeInitiateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    auth_service = AuthService(db)
    success, message = auth_service.initiate_email_change(
        str(current_user.id),
        body.current_password,
        body.new_email
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/email/verify-change", response_model=MessageResponse)
def verify_email_change(
    body: EmailChangeVerifyRequest,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    success, message = auth_service.verify_email_change(body.token)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    raw_token = auth_service.generate_password_reset_token(body.email)
    return {"message": "If an account with that email exists, a password reset link has been sent."}

@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    success = auth_service.reset_password(body.token, body.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired password reset token.")
    return {"message": "Your password has been reset successfully."}