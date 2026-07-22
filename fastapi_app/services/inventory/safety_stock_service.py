# fastapi_app/services/inventory/safety_stock_service.py
import math
from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload

from fastapi_app.models.inventory_model import InventorySKU, WarehouseInventory, SafetyStockCalculation
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
        """Calculate safety stock using formula: SS = Z × σ(d) × √L"""
        return z_score * demand_std_dev * math.sqrt(lead_time_days)

    @staticmethod
    def batch_calculate_safety_stock(
        db: Session,
        sku_list: List[str],
        service_level: float = 95,
    ) -> List[SafetyStockDetail]:
        """
        Calculate safety stock for multiple SKUs with batch commit.
        Uses relationships to avoid N+1 queries.
        """
        # ✅ Use joinedload to fetch SKU data in one query
        warehouses = db.query(WarehouseInventory).options(
            joinedload(WarehouseInventory.inventory_sku)
        ).filter(WarehouseInventory.sku.in_(sku_list)).all()
        
        results = []
        to_add = []
        
        for warehouse in warehouses:
            sku_record = warehouse.inventory_sku
            if not sku_record:
                continue
            
            z_score = SafetyStockService.calculate_z_score(service_level)
            demand_std_dev = warehouse.current_stock * 0.15  # TODO: Replace with real forecast
            
            recommended_safety_stock = SafetyStockService.calculate_safety_stock(
                z_score, demand_std_dev, sku_record.lead_time_days
            )
            
            variance_percentage = ((warehouse.current_stock - recommended_safety_stock) / recommended_safety_stock * 100) if recommended_safety_stock > 0 else 0
            
            if warehouse.current_stock >= recommended_safety_stock * 0.95:
                status = "optimal"
                recommendation = "optimal"
            elif warehouse.current_stock < recommended_safety_stock:
                status = "below_target"
                recommendation = "increase"
            else:
                status = "above_target"
                recommendation = "decrease"
            
            detail = SafetyStockDetail(
                sku=warehouse.sku,
                warehouse=warehouse.warehouse,
                region=warehouse.region,
                current_safety_stock=warehouse.current_stock,
                recommended_safety_stock=recommended_safety_stock,
                variance_percentage=variance_percentage,
                lead_time_days=sku_record.lead_time_days,
                demand_std_dev=demand_std_dev,
                service_level=service_level,
                status=status,
            )
            results.append(detail)
            
            # ✅ Batch add
            to_add.append(
                SafetyStockCalculation(
                    sku=warehouse.sku,
                    warehouse=warehouse.warehouse,
                    service_level=service_level,
                    z_score=z_score,
                    demand_std_dev=demand_std_dev,
                    lead_time_days=sku_record.lead_time_days,
                    calculated_safety_stock=recommended_safety_stock,
                    current_safety_stock=warehouse.current_stock,
                    recommendation=recommendation,
                )
            )
        
        # ✅ Single commit for all records
        if to_add:
            db.bulk_save_objects(to_add)
            db.commit()
        
        return results