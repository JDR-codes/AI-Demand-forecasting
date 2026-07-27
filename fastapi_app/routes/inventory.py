# fastapi_app/routes/inventory.py
"""
Inventory Router - Simplified endpoints matching Figma.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.inventory_schema import (
    InventoryDashboardResponse,
    UpdateStockRequest,
    UpdateStockResponse,
)
from fastapi_app.services.inventory.dashboard_service import InventoryDashboardService
from fastapi_app.services.inventory.alert_service import AlertService
from fastapi_app.services.inventory.inventory_update_service import InventoryUpdateService
from fastapi_app.services.inventory.export_service import InventoryExportService


router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard", response_model=InventoryDashboardResponse)
def get_inventory_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the complete inventory dashboard in one request."""
    try:
        return InventoryDashboardService.get_dashboard_data(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard: {str(e)}")


# ============================================================================
# ALERTS
# ============================================================================

@router.get("/alerts")
def get_inventory_alerts(
    is_read: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory alerts."""
    return AlertService.get_alerts(db, is_read, severity, limit, offset)


@router.post("/alerts/{alert_id}/mark-read")
def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an alert as read."""
    if not AlertService.mark_alert_read(db, alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert marked as read"}


# ============================================================================
# UPDATE STOCK
# ============================================================================

@router.post("/update-stock", response_model=UpdateStockResponse)
def update_stock(
    request: UpdateStockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update inventory stock level."""
    result = InventoryUpdateService.update_stock(
        db=db,
        sku=request.sku,
        warehouse=request.warehouse,
        new_quantity=request.new_quantity,
        reason=request.reason,
        user_id=current_user.id,
    )
    
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ============================================================================
# EXPORT
# ============================================================================

@router.get("/export")
def export_inventory_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export inventory report."""
    try:
        return InventoryExportService.export_inventory_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))