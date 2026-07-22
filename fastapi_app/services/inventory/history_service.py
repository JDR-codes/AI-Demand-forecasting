# fastapi_app/services/inventory/history_service.py
"""
Inventory History Service - Tracks all inventory changes.
"""
from typing import Optional
from sqlalchemy.orm import Session, Sessionfrom 
import datetime

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
        reference: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> InventoryHistory:
        """Record an inventory change in history."""
        history = InventoryHistory(
            sku=sku,
            warehouse=warehouse,
            old_stock=old_stock,
            new_stock=new_stock,
            change_amount=new_stock - old_stock,
            reason=reason,
            reference=reference,
            user_id=user_id,
            ip_address=ip_address,
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
        reference_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> InventoryMovement:
        """Record an inventory movement."""
        movement = InventoryMovement(
            sku=sku,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=quantity,
            reference_id=reference_id,
            created_by=user_id,
        )
        db.add(movement)
        db.commit()
        db.refresh(movement)
        return movement
    
    @staticmethod
    def get_history(
        db: Session,
        sku: Optional[str] = None,
        warehouse: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Get inventory history with filters."""
        query = db.query(InventoryHistory)
        if sku:
            query = query.filter(InventoryHistory.sku == sku)
        if warehouse:
            query = query.filter(InventoryHistory.warehouse == warehouse)
        
        total = query.count()
        items = query.order_by(
            InventoryHistory.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "pages": (total + limit - 1) // limit if limit > 0 and total > 0 else 1,
            "items": [
                {
                    "id": h.id,
                    "sku": h.sku,
                    "warehouse": h.warehouse,
                    "old_stock": h.old_stock,
                    "new_stock": h.new_stock,
                    "change_amount": h.change_amount,
                    "reason": h.reason,
                    "reference": h.reference,
                    "created_at": h.created_at,
                }
                for h in items
            ]
        }
    
    @staticmethod
    def get_movements(
        db: Session,
        sku: Optional[str] = None,
        warehouse: Optional[str] = None,
        movement_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Get inventory movements with filters."""
        query = db.query(InventoryMovement)
        if sku:
            query = query.filter(InventoryMovement.sku == sku)
        if warehouse:
            query = query.filter(InventoryMovement.warehouse == warehouse)
        if movement_type:
            query = query.filter(InventoryMovement.movement_type == movement_type)
        
        total = query.count()
        items = query.order_by(
            InventoryMovement.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "pages": (total + limit - 1) // limit if limit > 0 and total > 0 else 1,
            "items": [
                {
                    "id": m.id,
                    "sku": m.sku,
                    "warehouse": m.warehouse,
                    "movement_type": m.movement_type,
                    "quantity": m.quantity,
                    "reference_id": m.reference_id,
                    "created_at": m.created_at,
                }
                for m in items
            ]
        }
    
    @staticmethod
    def get_daily_movement_summary(db: Session) -> dict:
        """Get daily movement summary."""
        from sqlalchemy import func
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        movements = db.query(
            InventoryMovement.movement_type,
            func.sum(InventoryMovement.quantity).label('total_quantity'),
            func.count(InventoryMovement.id).label('count')
        ).filter(
            InventoryMovement.created_at >= today
        ).group_by(InventoryMovement.movement_type).all()
        
        return {
            "date": today.date().isoformat(),
            "movements": [
                {
                    "type": m.movement_type,
                    "total_quantity": float(m.total_quantity),
                    "count": m.count,
                }
                for m in movements
            ],
            "total_movements": sum(m.count for m in movements),
            "total_quantity": sum(m.total_quantity for m in movements),
        }