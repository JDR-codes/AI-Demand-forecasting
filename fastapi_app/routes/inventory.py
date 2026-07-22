# fastapi_app/routes/inventory.py
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.inventory_model import InventoryHistory, InventorySKU, InventoryTransfer
from fastapi_app.services.inventory.inventory_service import InventoryService
from fastapi_app.services.inventory.dashboard_service import InventoryDashboardService
from fastapi_app.schemas.inventory_schema import (
    InventoryHealthResponse,
    SafetyStockResponse,
    ReorderPointResponse,
    TransferOptimizationResponse,
    ExcessStockResponse,
    SlowMovingResponse,
    DashboardResponse,
    InventorySearchResponse,
)


router = APIRouter(prefix="/api/inventory", tags=["Inventory Optimization"])


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard", response_model=DashboardResponse)
def get_inventory_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the complete inventory dashboard in one request.
    """
    try:
        return InventoryDashboardService.get_dashboard_data(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard: {str(e)}")


# ============================================================================
# SAMPLE DATA
# ============================================================================

@router.post("/seed-sample-data")
def seed_sample_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seed database with enhanced sample inventory data.
    """
    try:
        InventoryService.seed_sample_inventory(db)
        return {
            "message": "Sample inventory data seeded successfully",
            "skus_created": 100,
            "warehouse_records_created": 300,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding data: {str(e)}")


# ============================================================================
# HEALTH
# ============================================================================

@router.get("/health", response_model=InventoryHealthResponse)
def get_inventory_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.get_inventory_health(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving inventory health: {str(e)}")


# ============================================================================
# SAFETY STOCK
# ============================================================================

@router.get("/safety-stock", response_model=SafetyStockResponse)
def get_safety_stock(
    service_level: float = Query(95, description="Service level percentage (90, 95, 97, 99, 99.9)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if service_level not in [90, 95, 97, 99, 99.9]:
        raise HTTPException(
            status_code=400,
            detail="Service level must be one of: 90, 95, 97, 99, 99.9",
        )
    try:
        return InventoryService.get_safety_stock_report(db, service_level)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving safety stock: {str(e)}")


# ============================================================================
# REORDER POINTS
# ============================================================================

@router.get("/reorder-points", response_model=ReorderPointResponse)
def get_reorder_points(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.get_reorder_points_report(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving reorder points: {str(e)}")


# ============================================================================
# TRANSFERS
# ============================================================================

@router.get("/transfers", response_model=TransferOptimizationResponse)
def get_transfer_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.get_transfer_recommendations(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving transfer recommendations: {str(e)}")


# ============================================================================
# EXCESS STOCK
# ============================================================================

@router.get("/excess-stock", response_model=ExcessStockResponse)
def get_excess_stock(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.get_excess_stock_report(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving excess stock: {str(e)}")


# ============================================================================
# SLOW MOVING
# ============================================================================

@router.get("/slow-moving", response_model=SlowMovingResponse)
def get_slow_moving(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        items = InventoryService.get_slow_moving_items(db)
        summary = {
            "total_items": len(items),
            "critical": sum(1 for i in items if i.status == "critical"),
            "high": sum(1 for i in items if i.status == "high"),
            "medium": sum(1 for i in items if i.status == "medium"),
            "low": sum(1 for i in items if i.status == "low"),
        }
        return SlowMovingResponse(data=items, total_items=len(items), summary=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving slow moving items: {str(e)}")


# ============================================================================
# WAREHOUSE ANALYTICS
# ============================================================================

@router.get("/warehouse-distribution")
def get_warehouse_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.get_warehouse_distribution(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving warehouse distribution: {str(e)}")


@router.get("/value-distribution")
def get_value_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.get_value_distribution(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving value distribution: {str(e)}")


@router.get("/warehouse-summary")
def get_warehouse_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.get_warehouse_summary(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving warehouse summary: {str(e)}")


# ============================================================================
# SEARCH
# ============================================================================

@router.get("/search", response_model=InventorySearchResponse)
def search_inventory(
    q: str = Query(..., description="Search query (SKU, product, warehouse, category, region)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InventoryService.search_inventory(db, q, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching inventory: {str(e)}")
    
# ============================================================================
# HISTORY & MOVEMENTS
# ============================================================================

@router.get("/history")
def get_inventory_history(
    sku: Optional[str] = None,
    warehouse: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory history."""
    from fastapi_app.services.inventory.history_service import InventoryHistoryService
    return InventoryHistoryService.get_history(db, sku, warehouse, limit, offset)


@router.get("/movements")
def get_inventory_movements(
    sku: Optional[str] = None,
    warehouse: Optional[str] = None,
    movement_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory movements."""
    from fastapi_app.services.inventory.history_service import InventoryHistoryService
    return InventoryHistoryService.get_movements(db, sku, warehouse, movement_type, limit, offset)


@router.get("/movements/daily-summary")
def get_daily_movement_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get daily movement summary."""
    from fastapi_app.services.inventory.history_service import InventoryHistoryService
    return InventoryHistoryService.get_daily_movement_summary(db)


# ============================================================================
# CHARTS
# ============================================================================

@router.get("/charts/inventory-trend")
def get_inventory_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory trend chart data."""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(
        func.date(InventoryHistory.created_at).label('date'),
        func.avg(InventoryHistory.new_stock).label('avg_stock')
    ).filter(
        InventoryHistory.created_at >= start_date
    ).group_by(func.date(InventoryHistory.created_at)).all()
    
    return {
        "labels": [h.date.strftime("%Y-%m-%d") for h in history],
        "values": [float(h.avg_stock) for h in history],
        "period": f"{days} days"
    }


@router.get("/charts/value-trend")
def get_value_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory value trend chart data."""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(
        func.date(InventoryHistory.created_at).label('date'),
        func.avg(InventoryHistory.new_stock * InventorySKU.unit_cost).label('avg_value')
    ).join(
        InventorySKU, InventoryHistory.sku == InventorySKU.sku
    ).filter(
        InventoryHistory.created_at >= start_date
    ).group_by(func.date(InventoryHistory.created_at)).all()
    
    return {
        "labels": [h.date.strftime("%Y-%m-%d") for h in history],
        "values": [float(h.avg_value) for h in history],
        "period": f"{days} days"
    }
    


# ============================================================================
# TRANSFER WORKFLOW
# ============================================================================

@router.post("/transfers/{transfer_id}/approve")
def approve_transfer(
    transfer_id: int,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a pending transfer."""
    from fastapi_app.services.inventory.transfer_workflow_service import TransferWorkflowService
    result = TransferWorkflowService.approve_transfer(db, transfer_id, current_user.id, notes)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/transfers/{transfer_id}/reject")
def reject_transfer(
    transfer_id: int,
    reason: str = Query(..., description="Reason for rejection"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject a pending transfer."""
    from fastapi_app.services.inventory.transfer_workflow_service import TransferWorkflowService
    result = TransferWorkflowService.reject_transfer(db, transfer_id, current_user.id, reason)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/transfers/{transfer_id}/dispatch")
def dispatch_transfer(
    transfer_id: int,
    vehicle: Optional[str] = None,
    driver: Optional[str] = None,
    tracking_number: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dispatch a transfer."""
    from fastapi_app.services.inventory.transfer_workflow_service import TransferWorkflowService
    result = TransferWorkflowService.dispatch_transfer(db, transfer_id, current_user.id, vehicle, driver, tracking_number)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/transfers/{transfer_id}/receive")
def receive_transfer(
    transfer_id: int,
    actual_quantity: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Receive a transfer at destination."""
    from fastapi_app.services.inventory.transfer_workflow_service import TransferWorkflowService
    result = TransferWorkflowService.receive_transfer(db, transfer_id, current_user.id, actual_quantity)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/transfers/{transfer_id}/complete")
def complete_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete a received transfer."""
    from fastapi_app.services.inventory.transfer_workflow_service import TransferWorkflowService
    result = TransferWorkflowService.complete_transfer(db, transfer_id, current_user.id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/transfers/{transfer_id}/cancel")
def cancel_transfer(
    transfer_id: int,
    reason: str = Query(..., description="Reason for cancellation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a transfer."""
    from fastapi_app.services.inventory.transfer_workflow_service import TransferWorkflowService
    result = TransferWorkflowService.cancel_transfer(db, transfer_id, current_user.id, reason)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


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
    from fastapi_app.services.inventory.alert_service import AlertService
    return AlertService.get_alerts(db, is_read, severity, limit, offset)


@router.post("/alerts/{alert_id}/mark-read")
def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an alert as read."""
    from fastapi_app.services.inventory.alert_service import AlertService
    if not AlertService.mark_alert_read(db, alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert marked as read"}


@router.post("/alerts/run-check")
def run_alert_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually run alert check."""
    from fastapi_app.services.inventory.alert_service import AlertService
    return AlertService.run_complete_alert_check(db)


# ============================================================================
# INVENTORY UPDATE
# ============================================================================

@router.post("/update-stock")
def update_stock(
    sku: str = Query(...),
    warehouse: str = Query(...),
    new_quantity: float = Query(...),
    reason: str = Query(...),
    reference: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update inventory stock level."""
    from fastapi_app.services.inventory.inventory_update_service import InventoryUpdateService
    result = InventoryUpdateService.update_stock(
        db=db,
        sku=sku,
        warehouse=warehouse,
        new_quantity=new_quantity,
        reason=reason,
        reference=reference,
        user_id=current_user.id,
        ip_address=current_user.email,  # Use email as identifier
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ============================================================================
# CACHE
# ============================================================================

@router.get("/cache/info")
def get_cache_info(
    current_user: User = Depends(get_current_user),
):
    """Get dashboard cache information."""
    from fastapi_app.services.inventory.dashboard_cache_service import DashboardCacheService
    return DashboardCacheService.get_cache_info()


@router.post("/cache/invalidate")
def invalidate_cache(
    current_user: User = Depends(get_current_user),
):
    """Invalidate dashboard cache."""
    from fastapi_app.services.inventory.dashboard_cache_service import DashboardCacheService
    DashboardCacheService.invalidate_cache()
    return {"message": "Cache invalidated"}


# ============================================================================
# CHARTS - Additional
# ============================================================================

@router.get("/charts/turnover-trend")
def get_turnover_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory turnover trend chart data."""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(
        func.date(InventoryHistory.created_at).label('date'),
        func.avg(InventoryHistory.change_amount / (InventoryHistory.old_stock + 1)).label('avg_turnover')
    ).filter(
        InventoryHistory.created_at >= start_date
    ).group_by(func.date(InventoryHistory.created_at)).all()
    
    return {
        "labels": [h.date.strftime("%Y-%m-%d") for h in history],
        "values": [float(h.avg_turnover) if h.avg_turnover else 0 for h in history],
        "period": f"{days} days"
    }


@router.get("/charts/carrying-cost-trend")
def get_carrying_cost_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get carrying cost trend chart data."""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(
        func.date(InventoryHistory.created_at).label('date'),
        func.avg(InventoryHistory.new_stock * 0.2).label('avg_cost')
    ).filter(
        InventoryHistory.created_at >= start_date
    ).group_by(func.date(InventoryHistory.created_at)).all()
    
    return {
        "labels": [h.date.strftime("%Y-%m-%d") for h in history],
        "values": [float(h.avg_cost) for h in history],
        "period": f"{days} days"
    }


@router.get("/charts/fill-rate-trend")
def get_fill_rate_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get fill rate trend chart data."""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(
        func.date(InventoryHistory.created_at).label('date'),
        func.avg(InventoryHistory.new_stock / (InventoryHistory.old_stock + 1) * 100).label('avg_fill_rate')
    ).filter(
        InventoryHistory.created_at >= start_date
    ).group_by(func.date(InventoryHistory.created_at)).all()
    
    return {
        "labels": [h.date.strftime("%Y-%m-%d") for h in history],
        "values": [float(h.avg_fill_rate) if h.avg_fill_rate else 0 for h in history],
        "period": f"{days} days"
    }


@router.get("/charts/transfer-volume")
def get_transfer_volume(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get transfer volume chart data."""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    transfers = db.query(
        func.date(InventoryTransfer.created_at).label('date'),
        func.sum(InventoryTransfer.transfer_quantity).label('total_quantity'),
        func.count(InventoryTransfer.id).label('count')
    ).filter(
        InventoryTransfer.created_at >= start_date
    ).group_by(func.date(InventoryTransfer.created_at)).all()
    
    return {
        "labels": [t.date.strftime("%Y-%m-%d") for t in transfers],
        "values": [float(t.total_quantity) for t in transfers],
        "counts": [t.count for t in transfers],
        "period": f"{days} days"
    }
    
# Add to fastapi_app/routes/inventory.py

# ============================================================================
# EXPORTS
# ============================================================================

@router.get("/export/inventory")
def export_inventory_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export inventory report."""
    from fastapi_app.services.inventory.export_service import InventoryExportService
    try:
        return InventoryExportService.export_inventory_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/warehouse")
def export_warehouse_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export warehouse report."""
    from fastapi_app.services.inventory.export_service import InventoryExportService
    try:
        return InventoryExportService.export_warehouse_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/transfers")
def export_transfer_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export transfer report."""
    from fastapi_app.services.inventory.export_service import InventoryExportService
    try:
        return InventoryExportService.export_transfer_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/safety-stock")
def export_safety_stock_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    service_level: float = Query(95, description="Service level percentage"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export safety stock report."""
    from fastapi_app.services.inventory.export_service import InventoryExportService
    try:
        return InventoryExportService.export_safety_stock_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/reorder")
def export_reorder_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export reorder report."""
    from fastapi_app.services.inventory.export_service import InventoryExportService
    try:
        return InventoryExportService.export_reorder_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/excess-stock")
def export_excess_stock_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export excess stock report."""
    from fastapi_app.services.inventory.export_service import InventoryExportService
    try:
        return InventoryExportService.export_excess_stock_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/slow-moving")
def export_slow_moving_report(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export slow moving inventory report."""
    from fastapi_app.services.inventory.export_service import InventoryExportService
    try:
        return InventoryExportService.export_slow_moving_report(db, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))