from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.modules.auth.auth_service import (
    create_super_admin,
    login_user
)
from fastapi_app.core.security import create_access_token
from fastapi_app.schemas.auth_schema import (
    SuperAdminCreate,
    UserLogin,
    UserOut,
    TokenResponse
)
from fastapi_app.models.auth_model import User

api_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@api_router.post("/super-admin/setup", response_model=UserOut)
def setup_superadmin(
    user_data: SuperAdminCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(
        User.role == "super_admin"
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin already exists"
        )

    return create_super_admin(db, user_data)


@api_router.post("/login", response_model=TokenResponse)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = login_user(db, user_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }