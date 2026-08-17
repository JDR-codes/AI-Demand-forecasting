# fastapi_app/schemas/role_schema.py
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
from datetime import datetime


class PermissionOut(BaseModel):
    """Response schema for a single permission."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModuleAccessItem(BaseModel):
    """Schema for a single module's access controls."""
    module_key: str
    module_name: str
    description: str
    read: bool = False
    write: bool = False
    delete: bool = False
    available_actions: List[str] = ["read", "write", "delete"]


class RoleCreate(BaseModel):
    """Schema for creating a new role."""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: List[int] = []
    
    # Role-level access control settings
    login_enabled: bool = True
    require_mfa: bool = False
    ip_restriction_enabled: bool = False
    allowed_ip_ranges: Optional[List[str]] = None
    session_timeout_hours: int = 8
    max_concurrent_sessions: int = 3
    
    # Module access settings
    module_access: Optional[Dict[str, Dict[str, bool]]] = None


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None
    
    # Role-level access control settings
    login_enabled: Optional[bool] = None
    require_mfa: Optional[bool] = None
    ip_restriction_enabled: Optional[bool] = None
    allowed_ip_ranges: Optional[List[str]] = None
    session_timeout_hours: Optional[int] = None
    max_concurrent_sessions: Optional[int] = None
    
    # Module access settings
    module_access: Optional[Dict[str, Dict[str, bool]]] = None


class RoleOut(BaseModel):
    """Response schema for a role."""
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_system_role: bool = False
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionOut] = []
    
    # Role-level access control settings
    login_enabled: bool = True
    require_mfa: bool = False
    ip_restriction_enabled: bool = False
    allowed_ip_ranges: Optional[List[str]] = None
    session_timeout_hours: int = 8
    max_concurrent_sessions: int = 3

    class Config:
        from_attributes = True


class RoleAccessControlsOut(BaseModel):
    """
    Schema for role access controls - shown in the Access Controls tab.
    """
    role_id: int
    role_name: str
    display_name: str
    is_system_role: bool
    
    # Access Control settings (role-level)
    login_enabled: bool
    require_mfa: bool
    ip_restriction_enabled: bool
    allowed_ip_ranges: Optional[List[str]]
    session_timeout_hours: int
    max_concurrent_sessions: int
    
    # Module-level permissions
    module_access: List[ModuleAccessItem]


class UpdateRoleAccessControlsRequest(BaseModel):
    """Request schema for updating a role's access controls."""
    # Role-level settings
    login_enabled: Optional[bool] = None
    require_mfa: Optional[bool] = None
    ip_restriction_enabled: Optional[bool] = None
    allowed_ip_ranges: Optional[List[str]] = None
    session_timeout_hours: Optional[int] = None
    max_concurrent_sessions: Optional[int] = None
    
    # Module permissions
    module_access: Optional[Dict[str, Dict[str, bool]]] = None