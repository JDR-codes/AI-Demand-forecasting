from fastapi_app import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.modules.auth.auth_service import get_user_by_id
from fastapi_app.core.security import verify_token


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Get current user from request Authorization header."""
    if not authorization or not authorization.startswith("Bearer"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid"
        )

    token = authorization.split(" ", 1)[1]
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


