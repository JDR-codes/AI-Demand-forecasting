# fastapi_app/services/inventory/warehouse_analytics_service.py
"""
Warehouse Analytics Service - Provides warehouse-level analytics.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi_app.models.inventory_model import WarehouseInventory, InventorySKU


class WarehouseAnalyticsService:
    """Service for warehouse analytics."""
    
    @staticmethod
    def get_warehouse_distribution(db: Session) -> List[Dict[str, Any]]:
        """Get units distribution by warehouse."""
        results = db.query(
            WarehouseInventory.warehouse,
            func.sum(WarehouseInventory.current_stock).label('total_units')
        ).group_by(WarehouseInventory.warehouse).all()
        
        total = sum(r.total_units for r in results)
        
        return [
            {
                "warehouse": r.warehouse,
                "total_units": float(r.total_units),
                "percentage": round((r.total_units / total * 100), 2) if total > 0 else 0,
            }
            for r in results
        ]
    
    @staticmethod
    def get_value_distribution(db: Session) -> List[Dict[str, Any]]:
        """Get inventory value distribution by warehouse."""
        # Join with InventorySKU to get unit cost
        results = db.query(
            WarehouseInventory.warehouse,
            func.sum(WarehouseInventory.current_stock * InventorySKU.unit_cost).label('total_value')
        ).join(
            InventorySKU, WarehouseInventory.sku == InventorySKU.sku
        ).group_by(WarehouseInventory.warehouse).all()
        
        total = sum(r.total_value for r in results)
        
        return [
            {
                "warehouse": r.warehouse,
                "inventory_value": float(r.total_value),
                "percentage": round((r.total_value / total * 100), 2) if total > 0 else 0,
            }
            for r in results
        ]
    
    @staticmethod
    def get_warehouse_summary(db: Session) -> List[Dict[str, Any]]:
        """Get warehouse summary with key metrics."""
        warehouses = db.query(WarehouseInventory.warehouse).distinct().all()
        summary = []
        
        for (warehouse,) in warehouses:
            inventory = db.query(WarehouseInventory).filter_by(warehouse=warehouse).all()
            
            if not inventory:
                continue
            
            total_units = sum(i.current_stock for i in inventory)
            total_value = 0
            item_types = set()
            low_stock = 0
            excess_stock = 0
            
            for i in inventory:
                sku = db.query(InventorySKU).filter_by(sku=i.sku).first()
                if sku:
                    total_value += i.current_stock * sku.unit_cost
                    if sku.category:
                        item_types.add(sku.category)
                
                # Determine stock status
                avg_stock = sum(ii.current_stock for ii in inventory) / len(inventory)
                if i.current_stock < avg_stock * 0.5:
                    low_stock += 1
                elif i.current_stock > avg_stock * 1.5:
                    excess_stock += 1
            
            # Get region
            region = inventory[0].region if inventory else "Unknown"
            
            summary.append({
                "warehouse": warehouse,
                "region": region,
                "total_units": round(total_units, 2),
                "inventory_value": round(total_value, 2),
                "item_types": len(item_types),
                "low_stock": low_stock,
                "excess_stock": excess_stock,
                "utilization": round((low_stock / len(inventory) * 100), 2) if inventory else 0,
            })
        
        return summary