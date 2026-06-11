from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

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

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response schema for login with token"""
    access_token: str
    token_type: str
    user: UserOut