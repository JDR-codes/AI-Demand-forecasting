from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.services.auth.auth_service import (
    create_super_admin,
    login_user,
    create_refresh_token_for_user,
    rotate_refresh_token,
    revoke_refresh_token,
    get_user_by_id,
    log_auth_event,
)

from fastapi_app.services.auth.password_reset_service import (
    request_password_reset_otp,
    verify_reset_otp,
    reset_user_password,
)
from fastapi_app.core.security import create_access_token
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.core.rate_limit import rate_limit, check_rate_limit
from fastapi_app.core.config import (
    COOKIE_SECURE,
    COOKIE_SAMESITE,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    OTP_SESSION_EXPIRE_MINUTES,
)
from fastapi_app.schemas.auth_schema import (
    SuperAdminCreate,
    UserLogin,
    UserOut,
    TokenResponse,
    MessageResponse,
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
    OtpResponse,
)
from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role

api_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# ─────────────────────────────────────────────────────────────────────────────
# Super admin bootstrap (one-time setup)
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
# POST /api/auth/login
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=900, scope="login"))],
)
def login(
    user_data: UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    check_rate_limit(f"login:{user_data.email}", max_requests=10, window_seconds=900)

    user = login_user(db, user_data)

    if not user:
        log_auth_event(db, user_data.email, "login_failed", success=False, ip_address=_client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.name if user.role else None, "type": "access"}
    )
    refresh_token_value = create_refresh_token_for_user(db, user)

    _set_session_cookies(response, access_token, refresh_token_value)
    log_auth_event(db, user_data.email, "login_success", success=True, ip_address=_client_ip(request))

    # Tokens are also returned in the body (in addition to the HTTP-only
    # cookies) for API clients / Swagger testing convenience — the cookies
    # are what actually secures a browser session; treat the body values
    # as a developer convenience, not the primary mechanism.
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
        "refresh_token": refresh_token_value,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revokes the refresh token tied to this session (so it can't be used to
    mint further access tokens) and clears both auth cookies. The current
    access token, if it hasn't expired yet, would still technically decode
    successfully until its own exp passes — access tokens are short-lived
    by design so this window is small; only the refresh token is tracked
    for revocation.
    """
    refresh_token_value = request.cookies.get("refresh_token")
    if refresh_token_value:
        revoke_refresh_token(db, refresh_token_value)

    _clear_session_cookies(response)
    log_auth_event(db, current_user.email, "logout", success=True, ip_address=_client_ip(request))

    return {"message": "Logged out successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/refresh-token
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post(
    "/refresh-token",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=900, scope="refresh"))],
)
def refresh_token_endpoint(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Reads the refresh token from the HTTP-only cookie (not the request
    body), rotates it — the old one is revoked and can't be reused — and
    sets fresh access_token + refresh_token cookies.
    """
    old_refresh_token = request.cookies.get("refresh_token")
    if not old_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh_token cookie found. Please log in again."
        )

    try:
        new_access_token, new_refresh_token, user = rotate_refresh_token(db, old_refresh_token)
    except ValueError as exc:
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    _set_session_cookies(response, new_access_token, new_refresh_token)
    log_auth_event(db, user.email, "token_refresh", success=True, ip_address=_client_ip(request))

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user": user,
        "refresh_token": new_refresh_token,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/forgot-password   (Step 1 — request OTP)
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post(
    "/forgot-password",
    response_model=OtpResponse,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=3600, scope="forgot-password"))],
)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    check_rate_limit(f"forgot-password:{payload.email}", max_requests=5, window_seconds=3600)
    try:
        result = request_password_reset_otp(db, payload.email)
        log_auth_event(db, payload.email, "password_reset_otp_requested", success=True,
                        ip_address=_client_ip(request))
        return result
    except ValueError as exc:
        log_auth_event(db, payload.email, "password_reset_otp_requested", success=False,
                        ip_address=_client_ip(request), detail=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/verify-otp   (Step 2 — verify OTP, get reset_token)
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post(
    "/verify-otp",
    response_model=OtpResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=3600, scope="verify-otp"))],
)
def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    check_rate_limit(f"verify-otp:{payload.email}", max_requests=10, window_seconds=3600)
    try:
        reset_token = verify_reset_otp(db, payload.email, payload.otp_code)
        log_auth_event(db, payload.email, "password_reset_otp_verified", success=True,
                        ip_address=_client_ip(request))
        return {
            "message": "OTP verified successfully. Use the reset_token to set your new password.",
            "reset_token": reset_token,
        }
    except ValueError as exc:
        log_auth_event(db, payload.email, "password_reset_otp_verified", success=False,
                        ip_address=_client_ip(request), detail=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/reset-password   (Step 3 — set new password)
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        reset_user_password(db, payload.email, payload.reset_token, payload.new_password)
        log_auth_event(db, payload.email, "password_reset_completed", success=True,
                        ip_address=_client_ip(request))
        return {"message": "Password has been reset successfully. You can now log in."}
    except ValueError as exc:
        log_auth_event(db, payload.email, "password_reset_completed", success=False,
                        ip_address=_client_ip(request), detail=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me
# ─────────────────────────────────────────────────────────────────────────────
@api_router.get("/me", response_model=UserOut)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user