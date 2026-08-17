#fastapi_app/services/inventory/excess_stock_service.py
"""
Excess Stock Service - Identifies excess inventory.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from fastapi_app.models.inventory_model import WarehouseInventory, ExcessStock


class ExcessStockService:
    """Service for identifying excess inventory."""

    EXCESS_LEVEL_THRESHOLDS = {
        "critical": 120,
        "high": 90,
        "medium": 60,
        "low": 30,
    }

    @staticmethod
    def determine_excess_level(days_inventory_on_hand: float) -> str:
        """Determine excess level based on DIOH."""
        if days_inventory_on_hand >= ExcessStockService.EXCESS_LEVEL_THRESHOLDS["critical"]:
            return "critical"
        elif days_inventory_on_hand >= ExcessStockService.EXCESS_LEVEL_THRESHOLDS["high"]:
            return "high"
        elif days_inventory_on_hand >= ExcessStockService.EXCESS_LEVEL_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    @staticmethod
    def identify_excess_stock(db: Session) -> Dict[str, Any]:
        """Identify all excess stock in the network."""
        excess_items = []

        all_inventory = db.query(WarehouseInventory).all()

        for warehouse_inv in all_inventory:
            # Mock forecasted demand (simplified)
            forecasted_demand_30days = warehouse_inv.current_stock * 0.15

            # Calculate excess quantity
            min_safe_level = warehouse_inv.safety_stock or warehouse_inv.current_stock * 0.1
            excess_quantity = max(0, warehouse_inv.current_stock - forecasted_demand_30days - min_safe_level)

            if excess_quantity <= 0:
                continue

            # Calculate days inventory on hand
            days_inventory_on_hand = (warehouse_inv.current_stock / forecasted_demand_30days * 30) if forecasted_demand_30days > 0 else 0

            if days_inventory_on_hand < ExcessStockService.EXCESS_LEVEL_THRESHOLDS["low"]:
                continue

            excess_level = ExcessStockService.determine_excess_level(days_inventory_on_hand)

            excess_items.append({
                "sku": warehouse_inv.sku,
                "warehouse": warehouse_inv.warehouse,
                "current_stock": warehouse_inv.current_stock,
                "days_inventory_on_hand": days_inventory_on_hand,
                "excess_quantity": excess_quantity,
                "excess_level": excess_level,
            })

            # Persist to database
            existing_row = db.query(ExcessStock).filter_by(
                sku=warehouse_inv.sku, warehouse=warehouse_inv.warehouse
            ).first()
            if existing_row:
                existing_row.current_stock = warehouse_inv.current_stock
                existing_row.excess_quantity = excess_quantity
                existing_row.days_inventory_on_hand = days_inventory_on_hand
                existing_row.excess_level = excess_level
            else:
                db.add(ExcessStock(
                    sku=warehouse_inv.sku,
                    warehouse=warehouse_inv.warehouse,
                    current_stock=warehouse_inv.current_stock,
                    excess_quantity=excess_quantity,
                    days_inventory_on_hand=days_inventory_on_hand,
                    excess_level=excess_level,
                ))

        db.commit()
        
        return {"excess_items": excess_items}