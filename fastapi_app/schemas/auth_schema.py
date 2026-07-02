from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime
import re
 
class UserLogin(BaseModel):
    """Schema for user/super_admin login"""
    email: EmailStr
    password: str
 
 
class SuperAdminCreate(BaseModel):
    """Schema for initial super_admin account creation (should be done via migration/script)"""
    name: str
    email: EmailStr
    password: str
    role: str = "super_admin"
 
 
class UserOut(BaseModel):
    """Response schema for user info"""
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: Optional[datetime]
 
    @field_validator("role", mode="before")
    @classmethod
    def role_name_from_relationship(cls, v):
        if v is None:
            return None
        if hasattr(v, "name"):
            return v.name
        return v
 
    class Config:
        from_attributes = True
 
 
class TokenResponse(BaseModel):
    """Response schema for login with token"""
    access_token: str
    token_type: str
    user: UserOut
    refresh_token: Optional[str] = None
 
 
class RefreshTokenRequest(BaseModel):
    """Schema for refreshing an access token"""
    refresh_token: str
 
 
class MessageResponse(BaseModel):
    """Generic message-only response (used for logout, etc.)"""
    message: str
 
 
# ── Password reset / forgot-password flow ──────────────────────────────────
 
class ForgotPasswordRequest(BaseModel):
    """Step 1 — User supplies email; backend sends OTP to their phone."""
    email: EmailStr
 
 
class VerifyOtpRequest(BaseModel):
    """Step 2 — User submits the OTP they received. Returns a reset_token."""
    email: EmailStr
    otp_code: str
 
 
class ResetPasswordRequest(BaseModel):
    """Step 3 — User submits new password along with the reset_token."""
    email: EmailStr
    reset_token: str
    new_password: str
    confirm_new_password: str
 
    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        return v
 
    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("new_password and confirm_new_password do not match.")
        return self
 
 
class OtpResponse(BaseModel):
    """Generic success/info response for OTP endpoints."""
    message: str
    reset_token: Optional[str] = None
    otp_code: Optional[str] = None  # Returned directly since there's no SMS provider