from typing import Optional, List
from sqlalchemy.orm import Session

from fastapi_app.models.role_model import Role
from fastapi_app.models.permission_model import Permission


def get_all_roles(db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
    return db.query(Role).order_by(Role.id).offset(skip).limit(limit).all()


def get_role(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()


def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(Role.name == name).first()


def get_all_permissions(db: Session) -> List[Permission]:
    """Permissions are a fixed, seeded catalog — this is read-only.
    See db/session.py _seed_rbac_defaults() for how the catalog is populated."""
    return db.query(Permission).order_by(Permission.id).all()


def _resolve_permissions(db: Session, permission_ids: List[int]) -> List[Permission]:
    if not permission_ids:
        return []

    permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    found_ids = {p.id for p in permissions}
    missing = set(permission_ids) - found_ids
    if missing:
        raise ValueError(f"permission_ids not found: {sorted(missing)}")
    return permissions


def create_role(db: Session, payload) -> Role:
    if get_role_by_name(db, payload.name):
        raise ValueError("A role with this name already exists")

    permissions = _resolve_permissions(db, payload.permission_ids)

    role = Role(name=payload.name, description=payload.description)
    role.permissions = permissions

    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, role_id: int, payload) -> Optional[Role]:
    role = get_role(db, role_id)
    if not role:
        return None

    update_data = payload.dict(exclude_unset=True)

    new_name = update_data.get("name")
    if new_name and new_name != role.name:
        existing = get_role_by_name(db, new_name)
        if existing and existing.id != role_id:
            raise ValueError("A role with this name already exists")

    if "permission_ids" in update_data:
        permission_ids = update_data.pop("permission_ids")
        role.permissions = _resolve_permissions(db, permission_ids) if permission_ids is not None else []

    for field, value in update_data.items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int) -> bool:
    """Delete a role. Returns False if it doesn't exist. Refuses to delete a
    role that still has users assigned to it, to avoid leaving users with a
    dangling/null role."""
    role = get_role(db, role_id)
    if not role:
        return False

    if role.users:
        raise ValueError(
            f"Cannot delete role '{role.name}': {len(role.users)} user(s) are still assigned to it. "
            f"Reassign them first."
        )

    db.delete(role)
    db.commit()
    return True