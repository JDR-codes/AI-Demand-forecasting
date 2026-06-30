from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PermissionOut(BaseModel):
    """Response schema for a single permission. Permissions are a fixed,
    seeded catalog — read-only via the API (GET /api/v1/permissions only)."""
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """Schema for POST /api/v1/roles."""
    name: str
    description: Optional[str] = None
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    """Schema for PUT /api/v1/roles/{id}. All fields optional — only fields
    that are sent get updated. Sending permission_ids replaces the role's
    entire permission set (not a merge)."""
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleOut(BaseModel):
    """Response schema for a role, including its assigned permissions."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    permissions: List[PermissionOut] = []

    class Config:
        from_attributes = True