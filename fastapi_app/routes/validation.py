from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.services.validation.validation_service import (
    get_validation_errors,
    get_validation_error,
    fix_validation_error,
    ignore_validation_error,
    fix_all_validation_errors,
)
from fastapi_app.schemas.validation_error_schema import (
    ValidationErrorOut,
    ValidationErrorFixRequest,
)
from fastapi_app.models.auth_model import User

router = APIRouter(prefix="/api/validation", tags=["Validation"])


@router.get("/errors", response_model=List[ValidationErrorOut])
def list_validation_errors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_validation_errors(db)


@router.get("/errors/{error_id}", response_model=ValidationErrorOut)
def get_validation_error_endpoint(
    error_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    err = get_validation_error(db, error_id)
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err


@router.post("/errors/{error_id}/fix", response_model=ValidationErrorOut)
def fix_validation_error_endpoint(
    error_id: int,
    payload: ValidationErrorFixRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    err = fix_validation_error(db, error_id, payload.dict())
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err


@router.post("/errors/{error_id}/ignore", response_model=ValidationErrorOut)
def ignore_validation_error_endpoint(
    error_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    err = ignore_validation_error(db, error_id)
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err


@router.post("/fix-all")
def fix_all_validation_errors_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = fix_all_validation_errors(db)
    return {"fixed_count": count}
