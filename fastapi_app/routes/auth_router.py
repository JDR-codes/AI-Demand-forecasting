from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.services.auth.auth_service import (
    create_super_admin,
    login_user,
    create_refresh_token_for_user,
    get_user_by_id,
)
from fastapi_app.services.auth.password_reset_service import (
    request_password_reset_otp,
    verify_reset_otp,
    reset_user_password,
)
from fastapi_app.core.security import create_access_token, verify_token
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.schemas.auth_schema import (
    SuperAdminCreate,
    UserLogin,
    UserOut,
    TokenResponse,
    RefreshTokenRequest,
    MessageResponse,
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
    OtpResponse,
)
from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role

api_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ─────────────────────────────────────────────────────────────────────────────
# Super admin bootstrap (one-time setup — not in the required list, kept as-is)
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/super-admin/setup", response_model=UserOut)
def setup_superadmin(
    user_data: SuperAdminCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(User).join(Role, User.role_id == Role.id).filter(
        Role.name == "super_admin"
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin already exists"
        )

    return create_super_admin(db, user_data)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/login
# ─────────────────────────────────────────────────────────────────────────────
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
        data={"sub": str(user.id), "role": user.role.name if user.role else None}
    )

    refresh_token_value = create_refresh_token_for_user(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
        "refresh_token": refresh_token_value,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/logout
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/logout", response_model=MessageResponse)
def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Stateless JWT logout — there's no server-side session to invalidate.
    The client is responsible for discarding the token. This endpoint exists
    mainly so the frontend has a clean call to make and to confirm the token
    was valid at the time of logout.
    """
    return {"message": "Logged out successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/refresh-token
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/refresh-token", response_model=TokenResponse)
def refresh_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        decoded = verify_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc)
        )

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token"
        )

    try:
        user_id = int(decoded.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.name if user.role else None}
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user": user
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/forgot-password   (Step 1 — request OTP)
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/forgot-password", response_model=OtpResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    try:
        return request_password_reset_otp(db, payload.email)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/verify-otp   (Step 2 — verify OTP, get reset_token)
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/verify-otp", response_model=OtpResponse)
def verify_otp(
    payload: VerifyOtpRequest,
    db: Session = Depends(get_db)
):
    try:
        reset_token = verify_reset_otp(db, payload.email, payload.otp_code)
        return {
            "message": "OTP verified successfully. Use the reset_token to set your new password.",
            "reset_token": reset_token,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/reset-password   (Step 3 — set new password)
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    try:
        reset_user_password(db, payload.email, payload.reset_token, payload.new_password)
        return {"message": "Password has been reset successfully. You can now log in."}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/auth/me
# ─────────────────────────────────────────────────────────────────────────────
@api_router.get("/me", response_model=UserOut)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user