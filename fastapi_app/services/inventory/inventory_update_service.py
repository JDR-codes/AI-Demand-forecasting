# fastapi_app/services/inventory/inventory_update_service.py
"""
Central Inventory Update Service - All inventory changes go through this service.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.models.inventory_model import WarehouseInventory, InventorySKU
from fastapi_app.services.inventory.history_service import InventoryHistoryService
from fastapi_app.services.inventory.alert_service import AlertService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.services.inventory.dashboard_cache_service import DashboardCacheService


class InventoryUpdateService:
    """Central service for all inventory updates."""
    
    @staticmethod
    def update_stock(
        db: Session,
        sku: str,
        warehouse: str,
        new_quantity: float,
        reason: str,
        reference: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        skip_validation: bool = False,
    ) -> Dict[str, Any]:
        """
        Update inventory stock level with full audit trail.
        This is the ONLY method that should modify current_stock.
        """
        # Get inventory record
        inventory = db.query(WarehouseInventory).filter(
            WarehouseInventory.sku == sku,
            WarehouseInventory.warehouse == warehouse
        ).first()
        
        if not inventory:
            return {"error": f"Inventory not found for SKU {sku} in warehouse {warehouse}"}
        
        # Validate negative inventory
        if new_quantity < 0 and not skip_validation:
            return {"error": "Cannot set negative inventory"}
        
        old_quantity = inventory.current_stock
        change_amount = new_quantity - old_quantity
        
        # Update stock
        inventory.current_stock = new_quantity
        inventory.updated_at = datetime.utcnow()
        
        # Update inventory value
        sku_record = db.query(InventorySKU).filter(InventorySKU.sku == sku).first()
        if sku_record:
            inventory.inventory_value = new_quantity * sku_record.unit_cost
        
        db.commit()
        
        # Record history
        InventoryHistoryService.record_history(
            db=db,
            sku=sku,
            warehouse=warehouse,
            old_stock=old_quantity,
            new_stock=new_quantity,
            reason=reason,
            reference=reference,
            user_id=user_id,
            ip_address=ip_address,
        )
        
        # Record movement
        movement_type = _determine_movement_type(reason, change_amount)
        InventoryHistoryService.record_movement(
            db=db,
            sku=sku,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=abs(change_amount),
            reference_id=reference,
            user_id=user_id,
        )
        
        # Check alerts
        if not skip_validation:
            AlertService.check_and_create_alerts(db, sku, warehouse, new_quantity)
        
        # Invalidate dashboard cache
        DashboardCacheService.invalidate_cache()
        
        # Send WebSocket update
        import asyncio
        asyncio.create_task(
            manager.send_dashboard_update({
                "type": "inventory_updated",
                "sku": sku,
                "warehouse": warehouse,
                "old_quantity": old_quantity,
                "new_quantity": new_quantity,
                "change": change_amount,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return {
            "success": True,
            "sku": sku,
            "warehouse": warehouse,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "change": change_amount,
            "inventory_value": inventory.inventory_value,
        }
    
    @staticmethod
    def bulk_update_stock(
        db: Session,
        updates: List[Dict[str, Any]],
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Bulk update inventory stock levels."""
        results = []
        errors = []
        
        for update in updates:
            result = InventoryUpdateService.update_stock(
                db=db,
                sku=update.get("sku"),
                warehouse=update.get("warehouse"),
                new_quantity=update.get("quantity"),
                reason=update.get("reason", "bulk_update"),
                reference=update.get("reference"),
                user_id=user_id,
                ip_address=ip_address,
                skip_validation=update.get("skip_validation", False),
            )
            
            if result.get("error"):
                errors.append(result)
            else:
                results.append(result)
        
        return {
            "success": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }


def _determine_movement_type(reason: str, change: float) -> str:
    """Determine movement type based on reason and change direction."""
    if change > 0:
        if "purchase" in reason.lower():
            return "purchase"
        elif "transfer" in reason.lower():
            return "transfer"
        elif "return" in reason.lower():
            return "return"
        else:
            return "adjustment"
    else:
        if "sale" in reason.lower():
            return "sale"
        elif "transfer" in reason.lower():
            return "transfer"
        elif "damage" in reason.lower():
            return "damage"
        else:
            return "adjustment"