# fastapi_app/routers/user_management.py
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.core.dependencies import (
    get_current_user, 
    require_permission_dep,
    require_users_read,
    require_users_write,
    require_users_delete,
)
from fastapi_app.core.permissions import require_permission, require_admin_or_super_admin, require_super_admin
from fastapi_app.core.config import ROLE_SUPER_ADMIN, PROTECTED_ROLES
from fastapi_app.core.module_permissions import MODULE_CATALOG
from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role
from fastapi_app.models.auth_audit_log_model import AuditLog
from fastapi_app.schemas.user_schema import (
    UserCreate, 
    UserUpdate, 
    UserManagementOut,
    UserInvite,
    UserManagementStats,
)
from fastapi_app.schemas.role_schema import (
    RoleCreate, 
    RoleUpdate, 
    RoleOut, 
    PermissionOut,
    RoleAccessControlsOut,
    UpdateRoleAccessControlsRequest,
    ModuleAccessItem,
)
from fastapi_app.services.users.user_service import (
    get_user_by_id,
    list_users,
    create_user,
    create_user_invite,
    update_user,
    delete_user,
    deactivate_user,
    count_active_super_admins,
    check_is_super_admin,
    get_actions_today_count,
    get_accessible_modules,
    get_user_management_stats,
)
from fastapi_app.services.roles.role_service import (
    get_all_roles,
    get_all_permissions,
    get_role,
    create_role,
    update_role,
    delete_role,
    get_role_access_controls,
)
from fastapi_app.services.auth.auth_service import log_auth_event, revoke_all_user_refresh_tokens

router = APIRouter(
    prefix="/api/users",
    tags=["User Management"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _check_last_active_super_admin(
    db: Session, 
    target_user: User, 
    block_deactivation_or_role_change: bool = False,
    current_user: User = None
) -> None:
    if not target_user.role or target_user.role.name != ROLE_SUPER_ADMIN:
        return

    if target_user.is_active:
        active_super_admins = count_active_super_admins(db)
        if active_super_admins <= 1:
            action = "deactivate or change the role of" if block_deactivation_or_role_change else "delete"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You cannot {action} the last active super_admin account in the system."
            )


def _log_audit_event(
    db: Session,
    event_type: str,
    success: bool,
    user: User,
    target_type: str = None,
    target_id: int = None,
    target_name: str = None,
    detail: str = None,
) -> None:
    try:
        audit_log = AuditLog(
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.name if user.role else None,
            event_type=event_type,
            success=success,
            action=event_type.replace("_", " ").title(),
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            detail=detail,
        )
        db.add(audit_log)
        db.commit()
    except Exception:
        db.rollback()


# ═════════════════════════════════════════════════════════════════════════════
# STATIC ROUTES (must come BEFORE dynamic /{user_id} routes)
# ═════════════════════════════════════════════════════════════════════════════

# GET /api/users/stats
@router.get("/stats", response_model=UserManagementStats)
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_users_read),
):
    """Get user management dashboard statistics."""
    return get_user_management_stats(db)


# GET /api/users/modules
@router.get("/modules", response_model=List[dict])
def list_available_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:read")),
):
    """Get the list of all available modules for the Access Controls tab."""
    modules = []
    for module_key, module in MODULE_CATALOG.items():
        modules.append({
            "module_key": module_key,
            "module_name": module["name"],
            "description": module["description"],
            "actions": module["actions"],
        })
    return modules


# ─────────────────────────────────────────────────────────────────────────────
# USER MANAGEMENT STATIC ROUTES
# ─────────────────────────────────────────────────────────────────────────────

# POST /api/users/invite
@router.post("/invite", response_model=UserManagementOut, status_code=status.HTTP_201_CREATED)
def invite_user_endpoint(
    payload: UserInvite,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_users_write),
):
    try:
        user = create_user_invite(db, payload, current_user)
        _log_audit_event(
            db, "user_invited", True, current_user,
            target_type="user", target_id=user.id, target_name=user.email,
            detail=f"User '{user.email}' invited by '{current_user.email}'"
        )
        out = UserManagementOut.model_validate(user)
        out.actions_today = get_actions_today_count(db, user.id)
        out.modules = get_accessible_modules(user)
        return out
    except ValueError as exc:
        _log_audit_event(
            db, "user_invited", False, current_user,
            target_type="user", target_name=payload.email,
            detail=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# POST /api/users
@router.post("", response_model=UserManagementOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_users_write),
):
    try:
        user = create_user(db, payload)
        _log_audit_event(
            db, "user_created", True, current_user,
            target_type="user", target_id=user.id, target_name=user.email,
            detail=f"User '{user.email}' created by '{current_user.email}'"
        )
        out = UserManagementOut.model_validate(user)
        out.actions_today = get_actions_today_count(db, user.id)
        out.modules = get_accessible_modules(user)
        return out
    except ValueError as exc:
        _log_audit_event(
            db, "user_created", False, current_user,
            target_type="user", target_name=payload.email,
            detail=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# ROLE MANAGEMENT STATIC ROUTES
# ─────────────────────────────────────────────────────────────────────────────

# GET /api/users/roles
@router.get("/roles", response_model=List[RoleOut])
def list_roles_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:read")),
):
    return get_all_roles(db)


# GET /api/users/permissions
@router.get("/permissions", response_model=List[PermissionOut])
def list_permissions_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:read")),
):
    return get_all_permissions(db)


# POST /api/users/roles
@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role_endpoint(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:write")),
):
    require_super_admin(current_user)
    
    try:
        role = create_role(db, payload, current_user)
        _log_audit_event(
            db, "role_created", True, current_user,
            target_type="role", target_id=role.id, target_name=role.name,
            detail=f"Role '{role.name}' created by '{current_user.email}'"
        )
        return role
    except ValueError as exc:
        _log_audit_event(
            db, "role_created", False, current_user,
            target_type="role", target_name=payload.name,
            detail=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC ROUTES (with path parameters - must come AFTER static routes)
# ─────────────────────────────────────────────────────────────────────────────

# GET /api/users/{user_id}
@router.get("/{user_id}", response_model=UserManagementOut)
def get_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_users_read),
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    out = UserManagementOut.model_validate(user)
    out.actions_today = get_actions_today_count(db, user.id)
    out.modules = get_accessible_modules(user)
    return out


# PUT /api/users/{user_id}
@router.put("/{user_id}", response_model=UserManagementOut)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_users_write),
):
    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if current_user.id == user_id:
        if payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account."
            )
        if payload.role_id is not None and payload.role_id != current_user.role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role to prevent self-lockout."
            )

    if payload.is_active is False or (payload.role_id is not None and payload.role_id != target_user.role_id):
        _check_last_active_super_admin(db, target_user, block_deactivation_or_role_change=True, current_user=current_user)

    try:
        updated = update_user(db, user_id, payload)
        if payload.is_active is False:
            revoke_all_user_refresh_tokens(db, user_id)
        
        changes = []
        if payload.name is not None:
            changes.append(f"name: {target_user.name} -> {payload.name}")
        if payload.email is not None:
            changes.append(f"email: {target_user.email} -> {payload.email}")
        if payload.role_id is not None:
            old_role = target_user.role.name if target_user.role else "None"
            new_role = updated.role.name if updated.role else "None"
            changes.append(f"role: {old_role} -> {new_role}")
        if payload.is_active is not None:
            changes.append(f"active: {target_user.is_active} -> {payload.is_active}")
        
        _log_audit_event(
            db, "user_updated", True, current_user,
            target_type="user", target_id=user_id, target_name=target_user.email,
            detail=f"User '{target_user.email}' updated by '{current_user.email}'. Changes: {', '.join(changes) if changes else 'No changes'}"
        )
        
        out = UserManagementOut.model_validate(updated)
        out.actions_today = get_actions_today_count(db, updated.id)
        out.modules = get_accessible_modules(updated)
        return out
    except ValueError as exc:
        _log_audit_event(
            db, "user_updated", False, current_user,
            target_type="user", target_id=user_id, target_name=target_user.email,
            detail=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# DELETE /api/users/{user_id}
@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user_endpoint(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_users_delete),
):
    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    _check_last_active_super_admin(db, target_user, block_deactivation_or_role_change=False, current_user=current_user)

    if target_user.role and target_user.role.name in PROTECTED_ROLES:
        if not current_user.role or current_user.role.name != ROLE_SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to delete a user with the '{target_user.role.name}' role."
            )

    revoke_all_user_refresh_tokens(db, user_id)

    if not delete_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    _log_audit_event(
        db, "user_deleted", True, current_user,
        target_type="user", target_id=user_id, target_name=target_user.email,
        detail=f"User '{target_user.email}' deleted by '{current_user.email}'"
    )

    return {"message": "User deleted successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# ROLE MANAGEMENT DYNAMIC ROUTES
# ─────────────────────────────────────────────────────────────────────────────

# GET /api/users/roles/{role_id}
@router.get("/roles/{role_id}", response_model=RoleOut)
def get_role_endpoint(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:read")),
):
    role = get_role(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found."
        )
    return role


# PUT /api/users/roles/{role_id}
@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role_endpoint(
    role_id: int,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:write")),
):
    try:
        role = update_role(db, role_id, payload, current_user)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found."
            )
        
        _log_audit_event(
            db, "role_updated", True, current_user,
            target_type="role", target_id=role_id, target_name=role.name,
            detail=f"Role '{role.name}' updated by '{current_user.email}'"
        )
        return role
    except ValueError as exc:
        _log_audit_event(
            db, "role_updated", False, current_user,
            target_type="role", target_id=role_id,
            detail=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# DELETE /api/users/roles/{role_id}
@router.delete("/roles/{role_id}", status_code=status.HTTP_200_OK)
def delete_role_endpoint(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:delete")),
):
    require_super_admin(current_user)
    
    try:
        if not delete_role(db, role_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found."
            )
        
        _log_audit_event(
            db, "role_deleted", True, current_user,
            target_type="role", target_id=role_id,
            detail=f"Role deleted by '{current_user.email}'"
        )
        return {"message": "Role deleted successfully."}
    except ValueError as exc:
        _log_audit_event(
            db, "role_deleted", False, current_user,
            target_type="role", target_id=role_id,
            detail=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# GET /api/users/roles/{role_id}/access-controls
@router.get("/roles/{role_id}/access-controls", response_model=RoleAccessControlsOut)
def get_role_access_controls_endpoint(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:read")),
):
    """Get a role's access control settings including module-level permissions."""
    access_controls = get_role_access_controls(db, role_id)
    if not access_controls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found."
        )
    return access_controls


# PUT /api/users/roles/{role_id}/access-controls
@router.put("/roles/{role_id}/access-controls", response_model=RoleAccessControlsOut)
def update_role_access_controls_endpoint(
    role_id: int,
    payload: UpdateRoleAccessControlsRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("roles:write")),
):
    """Update a role's access control settings including module-level permissions."""
    require_super_admin(current_user)
    
    role = get_role(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found."
        )
    
    update_data = payload.dict(exclude_unset=True)
    
    try:
        update_payload = RoleUpdate(**update_data)
        updated_role = update_role(db, role_id, update_payload, current_user)
        
        _log_audit_event(
            db, "role_access_controls_updated", True, current_user,
            target_type="role", target_id=role.id, target_name=role.name,
            detail=f"Access controls for role '{role.name}' updated by '{current_user.email}'"
        )
        
        return get_role_access_controls(db, role_id)
        
    except ValueError as exc:
        _log_audit_event(
            db, "role_access_controls_updated", False, current_user,
            target_type="role", target_id=role_id, target_name=role.name,
            detail=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )