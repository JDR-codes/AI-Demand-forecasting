# fastapi_app/services/inventory/inventory_update_service.py
"""
Central Inventory Update Service - All inventory changes go through this service.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.models.inventory_model import WarehouseInventory, InventorySKU
from fastapi_app.services.inventory.history_service import InventoryHistoryService
from fastapi_app.services.inventory.alert_service import AlertService
from fastapi_app.services.websocket.websocket_manager import manager


class InventoryUpdateService:
    """Central service for all inventory updates."""
    
    @staticmethod
    def update_stock(
        db: Session,
        sku: str,
        warehouse: str,
        new_quantity: float,
        reason: str,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update inventory stock level with full audit trail.
        This is the ONLY method that should modify current_stock.
        """
        inventory = db.query(WarehouseInventory).filter(
            WarehouseInventory.sku == sku,
            WarehouseInventory.warehouse == warehouse
        ).first()
        
        if not inventory:
            return {"error": f"Inventory not found for SKU {sku} in warehouse {warehouse}"}
        
        if new_quantity < 0:
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
            user_id=user_id,
        )
        
        # Check alerts
        AlertService.check_and_create_alerts(db, sku, warehouse, new_quantity)
        
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
            "message": f"Inventory updated successfully"
        }