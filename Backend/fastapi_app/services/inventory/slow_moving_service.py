# fastapi_app/services/inventory/slow_moving_service.py
"""
Slow Moving Inventory Service - Identifies slow-moving inventory.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.models.inventory_model import WarehouseInventory, InventorySKU, SlowMovingInventory


class SlowMovingService:
    """Service for slow-moving inventory analysis."""
    
    @staticmethod
    def get_slow_moving_items(db: Session) -> List[Dict[str, Any]]:
        """Get all slow-moving items with analysis."""
        all_inventory = db.query(WarehouseInventory).all()
        results = []
        
        for inv in all_inventory:
            # Calculate metrics (simplified)
            avg_daily_sales = inv.current_stock * 0.02
            days_in_stock = inv.current_stock / avg_daily_sales if avg_daily_sales > 0 else 0
            turnover_ratio = 365 / days_in_stock if days_in_stock > 0 else 0
            
            # Determine slow moving level
            if days_in_stock > 180:
                level = "critical"
            elif days_in_stock > 120:
                level = "high"
            elif days_in_stock > 60:
                level = "medium"
            else:
                level = "low"
            
            # Get SKU details
            sku_record = db.query(InventorySKU).filter_by(sku=inv.sku).first()
            product_name = sku_record.description if sku_record else inv.sku
            
            result = {
                "sku": inv.sku,
                "product_name": product_name,
                "warehouse": inv.warehouse,
                "current_stock": inv.current_stock,
                "turnover_ratio": round(turnover_ratio, 2),
                "days_in_stock": round(days_in_stock, 2),
                "slow_moving_level": level,
            }
            results.append(result)
            
            # Persist to database
            existing = db.query(SlowMovingInventory).filter_by(
                sku=inv.sku, warehouse=inv.warehouse
            ).first()
            if existing:
                existing.current_stock = inv.current_stock
                existing.days_in_stock = days_in_stock
                existing.turnover_ratio = turnover_ratio
                existing.slow_moving_level = level
                existing.updated_at = datetime.utcnow()
            else:
                db.add(SlowMovingInventory(
                    sku=inv.sku,
                    warehouse=inv.warehouse,
                    current_stock=inv.current_stock,
                    days_in_stock=days_in_stock,
                    turnover_ratio=turnover_ratio,
                    slow_moving_level=level,
                ))
        
        db.commit()
        return results