import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role
from fastapi_app.models.refresh_token_model import RefreshToken
from fastapi_app.models.auth_audit_log_model import AuditLog
from fastapi_app.models.auth_audit_log_model import AuditLog
from fastapi_app.core.security import (
    hash_password,
    verify_password,
    is_legacy_sha256_hash,
    create_access_token,
    verify_token,
)
from fastapi_app.core.config import REFRESH_TOKEN_EXPIRE_DAYS, ROLE_SUPER_ADMIN


def log_auth_event(
    db: Session,
    email: str | None,
    event_type: str,
    success: bool = True,
    ip_address: str | None = None,
    user_agent: str | None = None,
    detail: str | None = None,
    user_id: int | None = None,
    user_role: str | None = None,
) -> None:
    """Record an authentication event for the audit trail."""
    try:
        # Log to AuthAuditLog (legacy/auth-specific)
        db.add(
            AuditLog(
                email=email,
                event_type=event_type,
                success=success,
                ip_address=ip_address,
                user_agent=user_agent,
                detail=detail,
            )
        )
        
        # Also log to AuditLog (comprehensive) - works even without user_id
        db.add(
            AuditLog(
                user_id=user_id,  # Can be None for anonymous events
                user_email=email,
                user_role=user_role,
                event_type=event_type,
                success=success,
                action=event_type.replace("_", " ").title(),
                ip_address=ip_address,
                user_agent=user_agent,
                detail=detail,
            )
        )
        
        db.commit()
    except Exception:
        db.rollback()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(
        User.email == email,
        User.is_active == True
    ).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()


def get_user_by_id_any(db: Session, user_id: int):
    """Get user by ID regardless of active status."""
    return db.query(User).filter(User.id == user_id).first()


def _get_role_by_name(db: Session, name: str) -> Role:
    """Look up a seeded role by name."""
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        raise ValueError(
            f"Role '{name}' does not exist. Restart the app so it can be seeded."
        )
    return role


from datetime import datetime

def login_user(db: Session, user_data):
    user = get_user_by_email(db, user_data.email)

    if not user:
        return None

    if not verify_password(user_data.password, user.password):
        return None

    # Lazy migration: if this account still has its old, unsalted SHA-256
    # password hash, upgrade it to bcrypt now that we've confirmed the
    # plain-text password matches.
    if is_legacy_sha256_hash(user.password):
        user.password = hash_password(user_data.password)
        db.commit()

    # Update last_login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


def create_refresh_token_for_user(db: Session, user: User) -> str:
    """Create a long-lived refresh token and record its jti in `refresh_tokens`."""
    role_name = user.role.name if user.role else None
    jti = str(uuid.uuid4())
    expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    token = create_access_token(
        data={"sub": str(user.id), "role": role_name, "type": "refresh", "jti": jti},
        expires_delta=expires_delta,
    )

    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            revoked=False,
            expires_at=datetime.utcnow() + expires_delta,
        )
    )
    db.commit()

    return token


def rotate_refresh_token(db: Session, old_refresh_token: str) -> tuple[str, str, User]:
    """
    Validate an existing refresh token, revoke it, and issue a brand new
    access token + refresh token pair.
    """
    try:
        payload = verify_token(old_refresh_token)
    except ValueError as exc:
        raise ValueError(str(exc))

    if payload.get("type") != "refresh":
        raise ValueError("This is not a refresh token.")

    jti = payload.get("jti")
    stored = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()

    if not stored:
        raise ValueError("Refresh token not recognized.")
    if stored.revoked:
        raise ValueError("This refresh token has already been used or revoked. Please log in again.")
    if datetime.utcnow() > stored.expires_at:
        raise ValueError("Refresh token has expired. Please log in again.")

    user = get_user_by_id(db, int(payload.get("sub")))
    if not user:
        raise ValueError("User not found.")

    # Revoke the old one — rotation means it's single-use.
    stored.revoked = True
    db.commit()

    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.name if user.role else None, "type": "access"}
    )
    new_refresh_token = create_refresh_token_for_user(db, user)

    return new_access_token, new_refresh_token, user


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    """Revoke a refresh token (used on logout)."""
    try:
        payload = verify_token(refresh_token)
    except ValueError:
        return

    jti = payload.get("jti")
    if not jti:
        return

    stored = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if stored and not stored.revoked:
        stored.revoked = True
        db.commit()


def revoke_all_user_refresh_tokens(db: Session, user_id: int) -> None:
    """Revoke all refresh tokens for a user (used on password reset)."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    db.commit()


def check_super_admin_exists(db: Session) -> bool:
    """Check if any super admin exists in the system."""
    super_admin_role = db.query(Role).filter(Role.name == ROLE_SUPER_ADMIN).first()
    if not super_admin_role:
        return False
    
    count = db.query(User).filter(
        User.role_id == super_admin_role.id,
        User.is_active == True
    ).count()
    
    return count > 0