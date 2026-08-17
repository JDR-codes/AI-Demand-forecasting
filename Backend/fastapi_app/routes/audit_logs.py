from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime

from fastapi_app.db.session import get_db
from fastapi_app.core.dependencies import (
    get_current_user,
    require_permission_dep,
)
from fastapi_app.models.auth_model import User
from fastapi_app.models.auth_audit_log_model import AuditLog
from fastapi_app.schemas.audit_log_schema import (
    AuditLogOut,
    AuditLogListResponse,
    AuditLogExportItem,
)

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    search: Optional[str] = Query(None, description="Search in user_email, action, detail"),
    module: Optional[str] = Query(None, description="Filter by module/target_type"),
    success_filter: Optional[str] = Query(None, description="Filter by success status (true/false)"),
    date_from: Optional[datetime] = Query(None, description="Filter logs after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter logs before this date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("audit:read")),
):
    """List audit logs with filtering and pagination."""
    query = db.query(AuditLog)

    # Apply filters
    if search:
        query = query.filter(
            or_(
                AuditLog.user_email.ilike(f"%{search}%"),
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.detail.ilike(f"%{search}%"),
            )
        )

    if module:
        query = query.filter(AuditLog.target_type == module)

    if success_filter:
        success_bool = success_filter.lower() == "true"
        query = query.filter(AuditLog.success == success_bool)

    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)

    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    # Get total count before pagination
    total = query.count()

    # Apply pagination and ordering
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return AuditLogListResponse(
        items=logs,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{event_id}", response_model=AuditLogOut)
def get_audit_log_detail(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("audit:read")),
):
    """Get full details of a specific audit log event."""
    log = db.query(AuditLog).filter(AuditLog.id == event_id).first()
    if not log:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found."
        )
    return log


@router.get("/export", response_model=List[AuditLogExportItem])
def export_audit_logs(
    search: Optional[str] = Query(None, description="Search in user_email, action, detail"),
    module: Optional[str] = Query(None, description="Filter by module/target_type"),
    success_filter: Optional[str] = Query(None, description="Filter by success status (true/false)"),
    date_from: Optional[datetime] = Query(None, description="Filter logs after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter logs before this date"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum records to export"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("audit:read")),  # Changed from audit:manage to audit:read
):
    """
    Export audit logs as JSON (for CSV conversion by frontend).
    
    Anyone who can view audit logs (audit:read) can export them.
    audit:manage is reserved for future features like log retention configuration.
    """
    query = db.query(AuditLog)

    # Apply same filters as list endpoint
    if search:
        query = query.filter(
            or_(
                AuditLog.user_email.ilike(f"%{search}%"),
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.detail.ilike(f"%{search}%"),
            )
        )

    if module:
        query = query.filter(AuditLog.target_type == module)

    if success_filter:
        success_bool = success_filter.lower() == "true"
        query = query.filter(AuditLog.success == success_bool)

    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)

    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    return [AuditLogExportItem.from_orm(log) for log in logs]