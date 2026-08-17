# fastapi_app/core/permissions.py
from fastapi import HTTPException, status
from fastapi_app.models.auth_model import User
from fastapi_app.core.config import ROLE_SUPER_ADMIN, PROTECTED_ROLES

"""Permission helpers for role-based access control."""


def require_super_admin(user: User) -> None:
    """Require that the user has super_admin role."""
    if not user.role or user.role.name != ROLE_SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )


def require_admin_or_super_admin(user: User) -> None:
    """Require that the user has admin or super_admin role."""
    if not user.role or user.role.name not in (ROLE_SUPER_ADMIN, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )


def require_permission(user: User, permission_name: str) -> None:
    """Require that the user has a specific permission."""
    role_perms = user.role.permissions if (user.role and user.role.permissions) else []
    user_perms = user.permissions if user.permissions else []

    if not role_perms and not user_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no permissions assigned."
        )
    
    has_permission = any(p.name == permission_name for p in role_perms) or any(p.name == permission_name for p in user_perms)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission_name}' required"
        )


def is_protected_role(role_name: str) -> bool:
    """Check if a role is protected (cannot be modified/deleted by normal admins)."""
    return role_name in PROTECTED_ROLES


def can_modify_role(user: User, role_name: str) -> bool:
    """Check if a user can modify a specific role."""
    if not user.role:
        return False
    
    if user.role.name == ROLE_SUPER_ADMIN:
        return True
    
    if user.role.name == "admin":
        return not is_protected_role(role_name)
    
    return False