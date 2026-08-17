# fastapi_app/routes/validation.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.services.validation.validation_service import (
    get_validation_errors,
    get_validation_error,
    fix_validation_error,
    ignore_validation_error,
    fix_all_validation_errors,
    get_validation_statistics,
    auto_fix_all_validation_errors,
)
from fastapi_app.schemas.validation_error_schema import (
    ValidationErrorOut,
    ValidationErrorFixRequest,
    ValidationErrorIgnoreRequest,
    ValidationErrorBatchFixRequest,
    AutoFixResult,
)
from fastapi_app.models.auth_model import User

router = APIRouter(prefix="/api/validation", tags=["Validation"])

# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard")
def get_validation_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get validation statistics for dashboard."""
    return get_validation_statistics(db)

# ============================================================================
# ERROR LISTING - Only shows ACTIVE errors (open, not fixed, not ignored)
# ============================================================================

@router.get("/errors", response_model=List[ValidationErrorOut])
def list_validation_errors(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get validation errors with filters and pagination.
    Only returns ACTIVE errors (status='open', not fixed, not ignored)."""
    offset = (page - 1) * limit
    errors = get_validation_errors(
        db, severity, status, source, start_date, end_date, limit, offset
    )
    return errors


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


# ============================================================================
# FIX SINGLE ERROR
# ============================================================================

@router.patch("/errors/{error_id}/fix", response_model=ValidationErrorOut)
def fix_validation_error_endpoint(
    error_id: int,
    payload: ValidationErrorFixRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fix a validation error."""
    err = fix_validation_error(db, error_id, current_user.id, payload.comments)
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err


# ============================================================================
# IGNORE SINGLE ERROR
# ============================================================================

@router.patch("/errors/{error_id}/ignore", response_model=ValidationErrorOut)
def ignore_validation_error_endpoint(
    error_id: int,
    payload: ValidationErrorIgnoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ignore a validation error."""
    err = ignore_validation_error(db, error_id, current_user.id, payload.reason)
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@router.post("/errors/fix-all")
def fix_all_validation_errors_endpoint(
    payload: Optional[ValidationErrorBatchFixRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fix all open validation errors (manual)."""
    source = payload.source if payload else None
    comments = payload.reason if payload else None
    count = fix_all_validation_errors(db, current_user.id, source, comments)
    return {"fixed_count": count, "message": f"Fixed {count} validation errors"}


@router.post("/errors/auto-fix-all", response_model=AutoFixResult)
def auto_fix_all_validation_errors_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-fix all fixable validation errors."""
    return auto_fix_all_validation_errors(db, current_user.id)