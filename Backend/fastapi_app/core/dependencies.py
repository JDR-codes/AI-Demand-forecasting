# fastapi_app/core/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.services.auth.auth_service import get_user_by_id
from fastapi_app.core.security import verify_token
from fastapi_app.core.permissions import require_super_admin, require_permission

# This gives Swagger a simple "paste your token" Authorize box
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get current user from Bearer token OR HTTP-only cookie."""
    token = None
    
    # Try to get token from Authorization header first
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        # Fallback to cookie
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header or cookie missing"
        )

    try:
        payload = verify_token(token)
        user_id = int(payload.get("sub"))
    except (ValueError, TypeError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    return user


def get_current_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency for routes that should only be usable by a super_admin."""
    require_super_admin(current_user)
    return current_user


def require_permission_dep(permission_name: str):
    """Factory for creating permission-checking dependencies."""
    def _dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        require_permission(current_user, permission_name)
        return current_user
    return _dependency


def require_users_read(current_user: User = Depends(require_permission_dep("users:read"))):
    return current_user


def require_users_write(current_user: User = Depends(require_permission_dep("users:write"))):
    return current_user


def require_users_delete(current_user: User = Depends(require_permission_dep("users:delete"))):
    return current_user


def require_roles_read(current_user: User = Depends(require_permission_dep("roles:read"))):
    return current_user


def require_roles_write(current_user: User = Depends(require_permission_dep("roles:write"))):
    return current_user