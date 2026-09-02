from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user, get_db, require_permission_dep
from fastapi_app.models.auth_model import User
from fastapi_app.models.alert_model import AlertSeverity, AlertCategory
from fastapi_app.schemas.alert_schema import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    AlertReadResponse,
    AlertDeleteResponse,
)
from fastapi_app.services.alerts.alert_service import AlertService

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
def get_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="info | warning | critical"),
    category: Optional[AlertCategory] = Query(None, description="inventory | forecast | reorder | excess_stock | transfer | system"),
    is_read: Optional[bool] = Query(None, description="true | false"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("alerts:read")),
):
    """List all alerts — filter by severity, category, is_read"""
    return AlertService.get_alerts(db, severity=severity, category=category, is_read=is_read, skip=skip, limit=limit)


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("alerts:write")),
):
    """Create a new alert"""
    return AlertService.create_alert(db, payload)


@router.patch("/{alert_id}/read", response_model=AlertReadResponse)
def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("alerts:write")),
):
    """Mark a specific alert as read"""
    return AlertService.mark_as_read(db, alert_id)


@router.delete("/{alert_id}", response_model=AlertDeleteResponse)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("alerts:delete")),
):
    """Permanently delete an alert"""
    return AlertService.delete_alert(db, alert_id)