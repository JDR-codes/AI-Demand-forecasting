from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime
import re


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Response schema for user info"""
    id: int
    name: str
    email: EmailStr
    role: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

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


class MessageResponse(BaseModel):
    """Generic message-only response"""
    message: str


# ── Password reset / forgot-password flow ──────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    """Step 1 — User supplies email; backend sends OTP to their email."""
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    """Step 2 — User submits the OTP they received. Returns a reset_token."""
    email: EmailStr
    otp_code: str


class ResendOtpRequest(BaseModel):
    """Step 1.5 — User requests to resend OTP to their email."""
    email: EmailStr


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
    otp_code: Optional[str] = None