# fastapi_app/services/inventory/reorder_service.py
"""
Reorder Service - Calculates reorder points and status.
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from fastapi_app.models.inventory_model import WarehouseInventory, InventorySKU


class ReorderService:
    """Service for calculating reorder points."""
    
    @staticmethod
    def batch_calculate_reorder_points(db: Session) -> Dict[str, Any]:
        """
        Calculate reorder points for all SKUs.
        Returns simplified data for dashboard.
        """
        warehouses = db.query(WarehouseInventory).all()
        
        results = []
        
        for warehouse in warehouses:
            sku_record = db.query(InventorySKU).filter(InventorySKU.sku == warehouse.sku).first()
            if not sku_record:
                continue
            
            # Calculate metrics
            avg_daily_demand = warehouse.current_stock * 0.15 / 30
            safety_stock = warehouse.safety_stock or warehouse.current_stock * 0.1
            
            reorder_point = (avg_daily_demand * sku_record.lead_time_days) + safety_stock
            
            # Determine status
            if warehouse.current_stock <= reorder_point * 0.5:
                status = "URGENT_ORDER_NOW"
                days_until_stockout = int(warehouse.current_stock / avg_daily_demand) if avg_daily_demand > 0 else 0
            elif warehouse.current_stock <= reorder_point:
                status = "PLANNED_REORDER"
                days_until_stockout = int(warehouse.current_stock / avg_daily_demand) if avg_daily_demand > 0 else 0
            else:
                status = "SAFE"
                days_until_stockout = None
            
            # Map status for UI
            status_map = {"URGENT_ORDER_NOW": "Critical", "PLANNED_REORDER": "Low", "SAFE": "Optimal"}
            
            results.append({
                "sku": warehouse.sku,
                "product_name": sku_record.description or warehouse.sku,
                "warehouse": warehouse.warehouse,
                "current": warehouse.current_stock,
                "reorder_point": reorder_point,
                "safety_stock": safety_stock,
                "days_to_stockout": days_until_stockout,
                "status": status_map.get(status, status),
            })
        
        return {"data": results}