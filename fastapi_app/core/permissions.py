# fastapi_app/core/permissions.py

from fastapi import HTTPException, status
from fastapi_app.models.auth_model import User

"""Permission helpers for role-based access control."""


def require_super_admin(user: User) -> None:
    """Require that the user has super_admin role."""
    if not user.role or user.role.name != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )


def require_permission(user: User, permission_name: str) -> None:
    """Require that the user has a specific permission."""
    if not user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no role assigned"
        )
    
    if not user.role.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role has no permissions"
        )
    
    has_permission = any(p.name == permission_name for p in user.role.permissions)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission_name}' required"
        )