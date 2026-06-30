from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.services.auth.auth_service import get_user_by_id
from fastapi_app.core.security import verify_token
from fastapi_app.core.permissions import require_super_admin

# This gives Swagger a simple "paste your token" Authorize box —
# no username/password form, just a bearer token field.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get current user from the Bearer token (via Swagger's Authorize button or Authorization header)."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid"
        )

    token = credentials.credentials
    try:
        payload = verify_token(token)
        user_id = int(payload.get("sub"))
    except (ValueError, TypeError):
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

    return user


def get_current_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency for routes that should only be usable by a super_admin
    (e.g. the Roles & Permissions endpoints)."""
    require_super_admin(current_user)
    return current_user