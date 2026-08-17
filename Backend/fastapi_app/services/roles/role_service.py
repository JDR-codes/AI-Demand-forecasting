# fastapi_app/services/roles/role_service.py
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from fastapi_app.models.role_model import Role
from fastapi_app.models.permission_model import Permission
from fastapi_app.core.config import ROLE_SUPER_ADMIN, PROTECTED_ROLES
from fastapi_app.core.permissions import is_protected_role, can_modify_role
from fastapi_app.core.module_permissions import (
    MODULE_CATALOG, 
    get_module_permission, 
    get_permission_module
)
from fastapi_app.models.auth_model import User


def get_all_roles(db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
    return db.query(Role).order_by(Role.id).offset(skip).limit(limit).all()


def get_role(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()


def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(Role.name == name).first()


def get_all_permissions(db: Session) -> List[Permission]:
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


def _module_access_to_permission_names(module_access: Dict[str, Dict[str, bool]]) -> List[str]:
    """Convert module access dict to list of permission names."""
    permission_names = []
    
    for module_key, actions in module_access.items():
        module = MODULE_CATALOG.get(module_key)
        if not module:
            continue
        
        for action, enabled in actions.items():
            if enabled and action in module["actions"]:
                perm_name = module["permissions"].get(action)
                if perm_name:
                    permission_names.append(perm_name)
    
    return permission_names


def _permissions_to_module_access(permissions: List[Permission]) -> Dict[str, Dict[str, bool]]:
    """Convert list of permissions to module access dict."""
    module_access = {}
    
    for module_key, module in MODULE_CATALOG.items():
        module_access[module_key] = {action: False for action in module["actions"]}
    
    for perm in permissions:
        try:
            module_key, action = get_permission_module(perm.name)
            if module_key in module_access:
                module_access[module_key][action] = True
        except ValueError:
            pass
    
    return module_access


def create_role(db: Session, payload, created_by: Optional[User] = None) -> Role:
    """Create a new role with module access support."""
    if get_role_by_name(db, payload.name):
        raise ValueError("A role with this name already exists")

    permission_names = []
    
    if payload.module_access:
        permission_names = _module_access_to_permission_names(payload.module_access)
    elif payload.permission_ids:
        perm_ids = payload.permission_ids
        perms = db.query(Permission).filter(Permission.id.in_(perm_ids)).all()
        permission_names = [p.name for p in perms]
    
    all_perms = get_all_permissions(db)
    perm_map = {p.name: p for p in all_perms}
    
    permissions_to_assign = []
    for perm_name in permission_names:
        if perm_name in perm_map:
            permissions_to_assign.append(perm_map[perm_name])

    role = Role(
        name=payload.name,
        display_name=payload.display_name or payload.name.title(),
        description=payload.description,
        is_system_role=False,
        login_enabled=payload.login_enabled,
        require_mfa=payload.require_mfa,
        ip_restriction_enabled=payload.ip_restriction_enabled,
        allowed_ip_ranges=payload.allowed_ip_ranges,
        session_timeout_hours=payload.session_timeout_hours,
        max_concurrent_sessions=payload.max_concurrent_sessions,
    )
    role.permissions = permissions_to_assign

    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, role_id: int, payload, current_user: User) -> Optional[Role]:
    """Update a role with module access support."""
    role = get_role(db, role_id)
    if not role:
        return None

    if not can_modify_role(current_user, role.name):
        raise ValueError(f"You do not have permission to modify the '{role.name}' role.")

    update_data = payload.dict(exclude_unset=True)

    new_name = update_data.get("name")
    if new_name and new_name != role.name:
        if role.is_system_role:
            raise ValueError(f"Cannot rename the system role '{role.name}'.")
        
        existing = get_role_by_name(db, new_name)
        if existing and existing.id != role_id:
            raise ValueError("A role with this name already exists")

    module_access = update_data.pop("module_access", None)
    permission_ids = update_data.pop("permission_ids", None)
    
    if module_access is not None:
        permission_names = _module_access_to_permission_names(module_access)
        all_perms = get_all_permissions(db)
        perm_map = {p.name: p for p in all_perms}
        
        permissions_to_assign = []
        for perm_name in permission_names:
            if perm_name in perm_map:
                permissions_to_assign.append(perm_map[perm_name])
        
        role.permissions = permissions_to_assign
    elif permission_ids is not None:
        role.permissions = _resolve_permissions(db, permission_ids) if permission_ids is not None else []

    for field, value in update_data.items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int, current_user: User) -> bool:
    """Delete a role. Returns False if it doesn't exist."""
    role = get_role(db, role_id)
    if not role:
        return False

    if role.is_system_role:
        raise ValueError(f"Cannot delete the system role '{role.name}'.")

    if not can_modify_role(current_user, role.name):
        raise ValueError(f"You do not have permission to delete the '{role.name}' role.")

    if role.users:
        raise ValueError(
            f"Cannot delete role '{role.name}': {len(role.users)} user(s) are still assigned to it. "
            f"Reassign them first."
        )

    db.delete(role)
    db.commit()
    return True


def get_role_access_controls(db: Session, role_id: int) -> Optional[dict]:
    """Get a role's access controls including module permissions."""
    role = get_role(db, role_id)
    if not role:
        return None
    
    module_permissions = _permissions_to_module_access(role.permissions)
    
    module_access_items = []
    for module_key, module in MODULE_CATALOG.items():
        perms = module_permissions.get(module_key, {})
        item = {
            "module_key": module_key,
            "module_name": module["name"],
            "description": module["description"],
            "available_actions": module["actions"],
            "read": perms.get("read", False),
            "write": perms.get("write", False),
            "delete": perms.get("delete", False),
        }
        module_access_items.append(item)
    
    return {
        "role_id": role.id,
        "role_name": role.name,
        "display_name": role.display_name,
        "is_system_role": role.is_system_role,
        "login_enabled": role.login_enabled,
        "require_mfa": role.require_mfa,
        "ip_restriction_enabled": role.ip_restriction_enabled,
        "allowed_ip_ranges": role.allowed_ip_ranges,
        "session_timeout_hours": role.session_timeout_hours,
        "max_concurrent_sessions": role.max_concurrent_sessions,
        "module_access": module_access_items,
    }