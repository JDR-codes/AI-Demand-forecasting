# fastapi_app/services/inventory/alert_service.py
"""
Alert Service - Generates inventory alerts.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.models.inventory_model import WarehouseInventory, InventoryAlert


class AlertService:
    """Service for generating inventory alerts."""
    
    @staticmethod
    def check_and_create_alerts(
        db: Session,
        sku: str,
        warehouse: str,
        current_stock: float,
    ) -> List[InventoryAlert]:
        """Check conditions and create alerts for a specific SKU/warehouse."""
        alerts = []
        
        inventory = db.query(WarehouseInventory).filter(
            WarehouseInventory.sku == sku,
            WarehouseInventory.warehouse == warehouse
        ).first()
        
        if not inventory:
            return alerts
        
        reorder_point = inventory.reorder_point or inventory.current_stock * 0.2
        
        # 1. Critical stock alert
        if current_stock <= reorder_point * 0.5:
            alert = AlertService._create_alert(
                db=db,
                sku=sku,
                warehouse=warehouse,
                message=f"CRITICAL: SKU {sku} in {warehouse} is below 50% of reorder point. Current stock: {current_stock}",
                severity="critical"
            )
            alerts.append(alert)
        
        # 2. Reorder required alert
        elif current_stock <= reorder_point:
            alert = AlertService._create_alert(
                db=db,
                sku=sku,
                warehouse=warehouse,
                message=f"Reorder required for SKU {sku} in {warehouse}. Current stock: {current_stock}. Reorder point: {reorder_point}",
                severity="high"
            )
            alerts.append(alert)
        
        return alerts
    
    @staticmethod
    def _create_alert(
        db: Session,
        sku: str,
        warehouse: str,
        message: str,
        severity: str,
    ) -> InventoryAlert:
        """Create an alert record."""
        alert = InventoryAlert(
            sku=sku,
            warehouse=warehouse,
            message=message,
            severity=severity,
            is_read=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    def get_alerts(
        db: Session,
        is_read: Optional[bool] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get inventory alerts with filters."""
        query = db.query(InventoryAlert)
        
        if is_read is not None:
            query = query.filter(InventoryAlert.is_read == is_read)
        if severity:
            query = query.filter(InventoryAlert.severity == severity)
        
        total = query.count()
        items = query.order_by(
            InventoryAlert.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "pages": (total + limit - 1) // limit if limit > 0 and total > 0 else 1,
            "items": [
                {
                    "id": a.id,
                    "sku": a.sku,
                    "warehouse": a.warehouse,
                    "message": a.message,
                    "severity": a.severity,
                    "is_read": a.is_read,
                    "created_at": a.created_at,
                }
                for a in items
            ]
        }
    
    @staticmethod
    def mark_alert_read(db: Session, alert_id: int) -> bool:
        """Mark an alert as read."""
        alert = db.query(InventoryAlert).filter(InventoryAlert.id == alert_id).first()
        if not alert:
            return False
        
        alert.is_read = True
        alert.resolved_at = datetime.utcnow()
        db.commit()
        return True