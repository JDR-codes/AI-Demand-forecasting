from sqlalchemy.orm import Session

from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role
from fastapi_app.core.security import (
    hash_password,
    verify_password
)


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


def _get_role_by_name(db: Session, name: str) -> Role:
    """Look up a seeded role by name. Roles are auto-seeded on startup —
    see db/session.py _seed_rbac_defaults()."""
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        raise ValueError(
            f"Role '{name}' does not exist. Restart the app so it can be seeded, "
            f"or create it via POST /api/v1/roles."
        )
    return role


def create_super_admin(db: Session, user_data):
    existing = get_user_by_email(db, user_data.email)

    if existing:
        raise ValueError("Email already exists")

    super_admin_role = _get_role_by_name(db, "super_admin")

    user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
        role_id=super_admin_role.id,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def login_user(db: Session, user_data):
    user = get_user_by_email(db, user_data.email)

    if not user:
        return None

    if not verify_password(
        user_data.password,
        user.password
    ):
        return None

    return user

def create_user(db: Session, user_data):
    existing = get_user_by_email(db, user_data.email)

    if existing:
        raise ValueError("Email already exists")

    role_name = getattr(user_data, "role", None) or "user"
    role = _get_role_by_name(db, role_name)

    user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
        role_id=role.id,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_refresh_token_for_user(user: User):
    """Create a long-lived refresh token (7 days) for the given user."""
    from datetime import timedelta
    from fastapi_app.core.security import create_access_token

    role_name = user.role.name if user.role else None
    return create_access_token(
        data={"sub": str(user.id), "role": role_name, "type": "refresh"},
        expires_delta=timedelta(days=7),
    )