from sqlalchemy.orm import Session

from fastapi_app.models.auth_model import User
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


def create_super_admin(db: Session, user_data):
    existing = get_user_by_email(db, user_data.email)

    if existing:
        raise ValueError("Email already exists")

    user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
        role="super_admin",
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