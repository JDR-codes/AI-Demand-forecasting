from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.core.dependencies import get_current_super_admin
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.role_schema import RoleCreate, RoleUpdate, RoleOut, PermissionOut
from fastapi_app.services.roles.role_service import (
    get_all_roles,
    get_role,
    get_all_permissions,
    create_role,
    update_role,
    delete_role,
)

router = APIRouter(prefix="/api/roles", tags=["Roles & Permissions"])

# All endpoints in this router are super_admin only.


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/roles
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/roles", response_model=List[RoleOut])
def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    return get_all_roles(db, skip=skip, limit=limit)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/roles
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role_endpoint(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    try:
        return create_role(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/v1/roles/{id}
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role_endpoint(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    try:
        role = update_role(db, role_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/v1/roles/{id}
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/roles/{role_id}")
def delete_role_endpoint(
    role_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    role = get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Guard rail: don't let a super_admin delete the role currently assigned
    # to their own account, which would otherwise lock them out.
    if current_admin.role_id == role_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete the role currently assigned to your own account.",
        )

    try:
        if not delete_role(db, role_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return {"message": "Role deleted successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/permissions   (fixed catalog, read-only)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/permissions", response_model=List[PermissionOut])
def list_permissions(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    return get_all_permissions(db)