import math
from statistics import mean, stdev
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.models.inventory_model import (
    InventorySKU,
    WarehouseInventory,
    SafetyStockCalculation,
    ReorderPoint,
    ExcessStock,
)
from fastapi_app.schemas.inventory_schema import SafetyStockDetail


class SafetyStockService:
    """Service for calculating and managing safety stock levels."""

    SERVICE_LEVEL_Z_SCORES = {
        90: 1.28,
        95: 1.645,
        97: 1.88,
        99: 2.33,
        99.9: 3.09,
    }

    @staticmethod
    def calculate_z_score(service_level: float) -> float:
        """Get Z-score for given service level percentage."""
        if service_level in SafetyStockService.SERVICE_LEVEL_Z_SCORES:
            return SafetyStockService.SERVICE_LEVEL_Z_SCORES[service_level]
        # Linear interpolation for intermediate values
        sorted_levels = sorted(SafetyStockService.SERVICE_LEVEL_Z_SCORES.keys())
        for i in range(len(sorted_levels) - 1):
            if sorted_levels[i] < service_level < sorted_levels[i + 1]:
                x1, x2 = sorted_levels[i], sorted_levels[i + 1]
                y1, y2 = SafetyStockService.SERVICE_LEVEL_Z_SCORES[x1], SafetyStockService.SERVICE_LEVEL_Z_SCORES[x2]
                return y1 + (service_level - x1) * (y2 - y1) / (x2 - x1)
        return SafetyStockService.SERVICE_LEVEL_Z_SCORES[95]

    @staticmethod
    def calculate_safety_stock(
        z_score: float,
        demand_std_dev: float,
        lead_time_days: int,
    ) -> float:
        """
        Calculate safety stock using formula: SS = Z × σ(d) × √L
        
        Args:
            z_score: Service level Z-score
            demand_std_dev: Standard deviation of demand
            lead_time_days: Lead time in days
        
        Returns:
            Safety stock quantity
        """
        return z_score * demand_std_dev * math.sqrt(lead_time_days)

    @staticmethod
    def get_safety_stock_for_sku(
        db: Session,
        sku: str,
        warehouse: str,
        current_stock: float,
        demand_std_dev: float,
        lead_time_days: int,
        service_level: float = 95,
    ) -> SafetyStockDetail:
        """Calculate and return safety stock recommendation for a SKU."""
        z_score = SafetyStockService.calculate_z_score(service_level)
        recommended_safety_stock = SafetyStockService.calculate_safety_stock(
            z_score, demand_std_dev, lead_time_days
        )

        variance_percentage = ((current_stock - recommended_safety_stock) / recommended_safety_stock * 100) if recommended_safety_stock > 0 else 0

        if current_stock >= recommended_safety_stock * 0.95:
            status = "optimal"
        elif current_stock < recommended_safety_stock:
            status = "below_target"
        else:
            status = "above_target"

        # Get region from database
        warehouse_inv = db.query(WarehouseInventory).filter_by(sku=sku, warehouse=warehouse).first()
        region = warehouse_inv.region if warehouse_inv else "Unknown"

        return SafetyStockDetail(
            sku=sku,
            warehouse=warehouse,
            region=region,
            current_safety_stock=current_stock,
            recommended_safety_stock=recommended_safety_stock,
            variance_percentage=variance_percentage,
            lead_time_days=lead_time_days,
            demand_std_dev=demand_std_dev,
            service_level=service_level,
            status=status,
        )

    @staticmethod
    def batch_calculate_safety_stock(
        db: Session,
        sku_list: List[str],
        service_level: float = 95,
    ) -> List[SafetyStockDetail]:
        """Calculate safety stock for multiple SKUs."""
        results = []
        for sku in sku_list:
            warehouses = db.query(WarehouseInventory).filter_by(sku=sku).all()
            for warehouse_record in warehouses:
                z_score = SafetyStockService.calculate_z_score(service_level)
                # Mock demand_std_dev - in production, calculate from historical data
                demand_std_dev = warehouse_record.current_stock * 0.15  # 15% of current stock
                
                detail = SafetyStockService.get_safety_stock_for_sku(
                    db,
                    sku,
                    warehouse_record.warehouse,
                    warehouse_record.current_stock,
                    demand_std_dev,
                    warehouse_record.reorder_point or 7,  # Use stored lead time if available
                    service_level,
                )
                results.append(detail)
        return results
