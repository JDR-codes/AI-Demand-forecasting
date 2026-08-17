# fastapi_app/schemas/user_schema.py
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
import re

from fastapi_app.schemas.role_schema import RoleOut, PermissionOut


def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit.")
    return v


class UserCreate(BaseModel):
    """Schema for creating a new user through admin user management."""
    name: str
    email: EmailStr
    password: str
    role_id: int
    is_active: bool = True
    permission_ids: List[int] = []

    @field_validator("password")
    @classmethod
    def password_validation(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    """Schema for updating a user through admin user management."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None

    @field_validator("password")
    @classmethod
    def password_validation(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_password_strength(v)


class UserManagementOut(BaseModel):
    """Output schema for users under admin user management."""
    id: int
    name: str
    email: EmailStr
    is_active: bool
    status: str
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    role_id: Optional[int] = None
    role: Optional[RoleOut] = None
    permissions: List[PermissionOut] = []
    actions_today: int = 0
    modules: List[str] = []

    class Config:
        from_attributes = True


class UserInvite(BaseModel):
    """Schema for inviting a new user."""
    name: str
    email: EmailStr
    role_id: int
    permission_ids: List[int] = []


class UserManagementStats(BaseModel):
    """Dashboard stats for user management."""
    total_users: int
    active_now: int  # Active users with recent activity (last 5 minutes)
    pending_invites: int  # Users with status 'pending'
    actions_today: int  # Total audit actions today

    class Config:
        from_attributes = True