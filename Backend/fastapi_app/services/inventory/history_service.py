# fastapi_app/services/inventory/history_service.py
"""
Inventory History Service - Tracks all inventory changes.
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.models.inventory_model import InventoryHistory, InventoryMovement


class InventoryHistoryService:
    """Service for tracking inventory history and movements."""
    
    @staticmethod
    def record_history(
        db: Session,
        sku: str,
        warehouse: str,
        old_stock: float,
        new_stock: float,
        reason: str,
        user_id: Optional[int] = None,
    ) -> InventoryHistory:
        """Record an inventory change in history."""
        history = InventoryHistory(
            sku=sku,
            warehouse=warehouse,
            old_stock=old_stock,
            new_stock=new_stock,
            change_amount=new_stock - old_stock,
            reason=reason,
            user_id=user_id,
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    
    @staticmethod
    def record_movement(
        db: Session,
        sku: str,
        warehouse: str,
        movement_type: str,
        quantity: float,
        user_id: Optional[int] = None,
    ) -> InventoryMovement:
        """Record an inventory movement."""
        movement = InventoryMovement(
            sku=sku,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=quantity,
            created_by=user_id,
        )
        db.add(movement)
        db.commit()
        db.refresh(movement)
        return movement