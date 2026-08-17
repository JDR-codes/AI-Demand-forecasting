# fastapi_app/services/users/user_service.py
from datetime import datetime, timedelta
from typing import Optional, List, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role
from fastapi_app.models.permission_model import Permission
from fastapi_app.models.auth_audit_log_model import AuditLog
from fastapi_app.core.security import hash_password
from fastapi_app.core.config import ROLE_SUPER_ADMIN, PROTECTED_ROLES
from fastapi_app.schemas.user_schema import UserCreate, UserUpdate, UserInvite


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Retrieve a user by ID, including inactive users."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email_any(db: Session, email: str) -> Optional[User]:
    """Retrieve a user by email, including inactive users."""
    return db.query(User).filter(User.email.ilike(email)).first()


def _resolve_permissions(db: Session, permission_ids: List[int]) -> List[Permission]:
    """Resolve a list of permission IDs to Permission models. Raises ValueError if any ID is invalid."""
    if not permission_ids:
        return []

    permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    found_ids = {p.id for p in permissions}
    missing = set(permission_ids) - found_ids
    if missing:
        raise ValueError(f"permission_ids not found: {sorted(missing)}")
    return permissions


def list_users(
    db: Session,
    search: Optional[str] = None,
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[User]:
    """List users with optional search, role filter, active status filter, and pagination."""
    query = db.query(User)

    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    if role_id is not None:
        query = query.filter(User.role_id == role_id)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.order_by(User.id.asc()).offset(skip).limit(limit).all()


def create_user(db: Session, payload: UserCreate) -> User:
    """Create a new user."""
    existing_user = get_user_by_email_any(db, payload.email)
    if existing_user:
        raise ValueError("A user with this email address already exists.")

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise ValueError("The selected role does not exist.")

    permissions = _resolve_permissions(db, payload.permission_ids)
    hashed_password = hash_password(payload.password)

    user = User(
        name=payload.name,
        email=payload.email,
        password=hashed_password,
        initial_password_hash=hashed_password,
        role_id=payload.role_id,
        is_active=payload.is_active,
        status="active" if payload.is_active else "inactive",
    )
    user.permissions = permissions

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_invite(db: Session, payload: UserInvite, inviter: User) -> User:
    """Create a pending user invite."""
    existing_user = get_user_by_email_any(db, payload.email)
    if existing_user:
        raise ValueError("A user with this email address already exists.")

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise ValueError("The selected role does not exist.")

    # Generate a random unusable password placeholder
    import secrets
    random_password = secrets.token_urlsafe(32)

    permissions = _resolve_permissions(db, payload.permission_ids)

    user = User(
        name=payload.name,
        email=payload.email,
        password=hash_password(random_password),
        initial_password_hash=None,
        role_id=payload.role_id,
        is_active=False,
        status="pending",
    )
    user.permissions = permissions

    db.add(user)
    db.commit()
    db.refresh(user)

    # Send invite email
    try:
        from fastapi_app.utils.email_utils import send_invite_email
        # Generate invite token (would be a separate endpoint)
        # For now, this is a placeholder - actual implementation would create
        # a token and send a proper invite link
        invite_link = f"/accept-invite?email={payload.email}&user_id={user.id}"
        send_invite_email(payload.email, payload.name, inviter.name, invite_link)
    except Exception:
        # Log error but don't fail the request
        # The user is created, they can resend the invite
        pass

    return user


def update_user(db: Session, user_id: int, payload: UserUpdate) -> Optional[User]:
    """Update user information."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    update_data = payload.dict(exclude_unset=True)

    if "email" in update_data:
        new_email = update_data["email"]
        if new_email and new_email.lower() != user.email.lower():
            existing_user = get_user_by_email_any(db, new_email)
            if existing_user:
                raise ValueError("A user with this email address already exists.")

    if "role_id" in update_data:
        new_role_id = update_data["role_id"]
        if new_role_id is not None:
            role = db.query(Role).filter(Role.id == new_role_id).first()
            if not role:
                raise ValueError("The selected role does not exist.")

    if "permission_ids" in update_data:
        permission_ids = update_data.pop("permission_ids")
        user.permissions = _resolve_permissions(db, permission_ids) if permission_ids is not None else []

    if "status" in update_data:
        status_val = update_data["status"]
        if status_val == "active":
            user.is_active = True
        elif status_val == "inactive" or status_val == "pending":
            user.is_active = False

    if "password" in update_data:
        new_password = update_data.pop("password")
        if new_password:
            user.password = hash_password(new_password)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user. Returns False if they don't exist."""
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True


def deactivate_user(db: Session, user_id: int) -> Optional[User]:
    """Deactivate a user instead of deleting them."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    user.is_active = False
    user.status = "inactive"
    db.commit()
    db.refresh(user)
    return user


def check_is_super_admin(db: Session, user_id: int) -> bool:
    """Check if a user is a super admin."""
    user = get_user_by_id(db, user_id)
    if not user or not user.role:
        return False
    return user.role.name == ROLE_SUPER_ADMIN


def count_active_super_admins(db: Session) -> int:
    """Count active super admin users."""
    super_admin_role = db.query(Role).filter(Role.name == ROLE_SUPER_ADMIN).first()
    if not super_admin_role:
        return 0
    
    return db.query(User).filter(
        User.role_id == super_admin_role.id,
        User.is_active == True
    ).count()


def get_actions_today_count(db: Session, user_id: int) -> int:
    """Count audit log entries for a user today."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.created_at >= today_start
    ).count()


def get_accessible_modules(user: User) -> List[str]:
    """Derive distinct module names from user's effective permissions."""
    role_perms = user.role.permissions if (user.role and user.role.permissions) else []
    user_perms = user.permissions if user.permissions else []
    
    all_perms = list(role_perms) + list(user_perms)
    
    modules: Set[str] = set()
    for perm in all_perms:
        if ':' in perm.name:
            module = perm.name.split(':')[0]
            modules.add(module)
    
    return sorted(list(modules))


def get_user_management_stats(db: Session) -> dict:
    """Get dashboard stats for user management."""
    # Total users
    total_users = db.query(User).count()
    
    # Active now (last 5 minutes)
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    active_now = db.query(User).filter(
        User.is_active == True,
        User.last_login >= five_minutes_ago
    ).count()
    
    # Pending invites
    pending_invites = db.query(User).filter(User.status == "pending").count()
    
    # Actions today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    actions_today = db.query(AuditLog).filter(
        AuditLog.created_at >= today_start
    ).count()
    
    # Role breakdown
    role_counts = db.query(
        Role.id,
        Role.display_name,
        func.count(User.id).label('count')
    ).outerjoin(User, User.role_id == Role.id).group_by(Role.id, Role.display_name).all()
    
    role_breakdown = [
        {"id": r.id, "display_name": r.display_name, "count": r.count}
        for r in role_counts
    ]
    
    return {
        "total_users": total_users,
        "active_now": active_now,
        "pending_invites": pending_invites,
        "actions_today": actions_today,
        "role_breakdown": role_breakdown,
    }