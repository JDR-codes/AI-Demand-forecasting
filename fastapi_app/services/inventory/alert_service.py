# fastapi_app/services/inventory/alert_service.py
"""
Alert Service - Automatically generates inventory alerts.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.models.inventory_model import (
    WarehouseInventory,
    InventoryAlert,
    InventorySKU,
    InventoryTransfer,
    ReorderPoint,
    ExcessStock,
    SlowMovingInventory,
)
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.services.websocket.websocket_manager import manager


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
        
        # Get inventory data
        inventory = db.query(WarehouseInventory).filter(
            WarehouseInventory.sku == sku,
            WarehouseInventory.warehouse == warehouse
        ).first()
        
        if not inventory:
            return alerts
        
        reorder_point = inventory.reorder_point or inventory.current_stock * 0.2
        safety_stock = inventory.safety_stock or inventory.current_stock * 0.1
        
        # 1. Critical stock alert
        if current_stock <= reorder_point * 0.5:
            alert = AlertService._create_alert(
                db=db,
                sku=sku,
                warehouse=warehouse,
                alert_type="critical_stock",
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
                alert_type="reorder_needed",
                message=f"Reorder required for SKU {sku} in {warehouse}. Current stock: {current_stock}. Reorder point: {reorder_point}",
                severity="high"
            )
            alerts.append(alert)
        
        # 3. Safety stock violation
        if current_stock < safety_stock:
            alert = AlertService._create_alert(
                db=db,
                sku=sku,
                warehouse=warehouse,
                alert_type="safety_stock_violation",
                message=f"Safety stock violation for SKU {sku} in {warehouse}. Current stock: {current_stock}. Safety stock: {safety_stock}",
                severity="high"
            )
            alerts.append(alert)
        
        # 4. Negative inventory
        if current_stock < 0:
            alert = AlertService._create_alert(
                db=db,
                sku=sku,
                warehouse=warehouse,
                alert_type="negative_inventory",
                message=f"NEGATIVE INVENTORY detected for SKU {sku} in {warehouse}. Current stock: {current_stock}",
                severity="critical"
            )
            alerts.append(alert)
        
        return alerts
    
    @staticmethod
    def _create_alert(
        db: Session,
        sku: str,
        warehouse: str,
        alert_type: str,
        message: str,
        severity: str,
    ) -> InventoryAlert:
        """Create an alert record."""
        alert = InventoryAlert(
            sku=sku,
            warehouse=warehouse,
            alert_type=alert_type,
            message=message,
            severity=severity,
            is_read=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    async def _send_alert_notification(title: str, message: str, priority: str):
        """Send alert notification."""
        await manager.broadcast({
            "type": "inventory_alert",
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    def run_complete_alert_check(db: Session) -> Dict[str, Any]:
        """Run complete alert check for all inventory."""
        all_inventory = db.query(WarehouseInventory).all()
        total_alerts = 0
        
        for inventory in all_inventory:
            alerts = AlertService.check_and_create_alerts(
                db=db,
                sku=inventory.sku,
                warehouse=inventory.warehouse,
                current_stock=inventory.current_stock,
            )
            total_alerts += len(alerts)
        
        # Check excess stock alerts
        excess_items = db.query(ExcessStock).filter(
            ExcessStock.excess_level.in_(["critical", "high"])
        ).all()
        
        for item in excess_items:
            alert = AlertService._create_alert(
                db=db,
                sku=item.sku,
                warehouse=item.warehouse,
                alert_type="excess_stock",
                message=f"Excess stock detected for {item.sku} in {item.warehouse}. Excess quantity: {item.excess_quantity}. Level: {item.excess_level}",
                severity="high" if item.excess_level == "critical" else "medium"
            )
            total_alerts += 1
        
        # Check slow moving alerts
        slow_items = db.query(SlowMovingInventory).filter(
            SlowMovingInventory.slow_moving_level.in_(["critical", "high"])
        ).all()
        
        for item in slow_items:
            alert = AlertService._create_alert(
                db=db,
                sku=item.sku,
                warehouse=item.warehouse,
                alert_type="slow_moving",
                message=f"Slow moving inventory detected for {item.sku} in {item.warehouse}. Days in stock: {item.days_in_stock}. Level: {item.slow_moving_level}",
                severity="high" if item.slow_moving_level == "critical" else "medium"
            )
            total_alerts += 1
        
        # Check failed transfers
        failed_transfers = db.query(InventoryTransfer).filter(
            InventoryTransfer.status == "cancelled"
        ).all()
        
        for transfer in failed_transfers:
            if transfer.updated_at and (datetime.utcnow() - transfer.updated_at).days < 1:
                alert = AlertService._create_alert(
                    db=db,
                    sku=transfer.sku,
                    warehouse=transfer.from_warehouse,
                    alert_type="transfer_failed",
                    message=f"Transfer failed for {transfer.sku} from {transfer.from_warehouse} to {transfer.to_warehouse}",
                    severity="high"
                )
                total_alerts += 1
        
        return {
            "total_alerts_created": total_alerts,
            "message": f"Alert check completed. Created {total_alerts} alerts.",
            "timestamp": datetime.utcnow().isoformat()
        }
    
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
                    "alert_type": a.alert_type,
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