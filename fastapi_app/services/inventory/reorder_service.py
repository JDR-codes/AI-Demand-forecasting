# fastapi_app/services/inventory/reorder_service.py
import math
from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta

from fastapi_app.models.inventory_model import InventorySKU, WarehouseInventory, ReorderPoint as ReorderPointModel
from fastapi_app.schemas.inventory_schema import ReorderPointDetail


class ReorderService:
    """Service for calculating reorder points and economic order quantities."""

    @staticmethod
    def calculate_economic_order_quantity(
        annual_demand: float,
        order_cost: float,
        holding_cost: float,
    ) -> float:
        """Calculate EOQ using formula: EOQ = √(2DS/H)"""
        if holding_cost <= 0:
            return 0
        return math.sqrt((2 * annual_demand * order_cost) / holding_cost)

    @staticmethod
    def calculate_reorder_point(
        avg_daily_demand: float,
        lead_time_days: int,
        safety_stock: float,
    ) -> float:
        """Calculate reorder point using formula: ROP = (Avg Daily Demand × Lead Time) + Safety Stock"""
        return (avg_daily_demand * lead_time_days) + safety_stock

    @staticmethod
    def determine_reorder_status(
        current_stock: float,
        reorder_point: float,
        avg_daily_demand: float,
    ) -> Tuple[str, int]:
        """Determine reorder status and days until stockout."""
        if current_stock <= reorder_point * 0.5:
            status = "URGENT_ORDER_NOW"
            days_until_stockout = int(current_stock / avg_daily_demand) if avg_daily_demand > 0 else 0
        elif current_stock <= reorder_point:
            status = "PLANNED_REORDER"
            days_until_stockout = int(current_stock / avg_daily_demand) if avg_daily_demand > 0 else 0
        else:
            status = "SAFE"
            days_until_stockout = None
        return status, days_until_stockout

    @staticmethod
    def batch_calculate_reorder_points(
        db: Session,
        sku_list: List[str],
    ) -> Tuple[List[ReorderPointDetail], int, int]:
        """
        Calculate reorder points for multiple SKUs with batch commit.
        Uses relationships to avoid N+1 queries.
        """
        # ✅ Use joinedload to fetch SKU data in one query
        warehouses = db.query(WarehouseInventory).options(
            joinedload(WarehouseInventory.inventory_sku)
        ).filter(WarehouseInventory.sku.in_(sku_list)).all()
        
        urgent_count = 0
        planned_count = 0
        results = []
        to_add = []
        
        for warehouse in warehouses:
            sku_record = warehouse.inventory_sku
            if not sku_record:
                continue
            
            # Calculate metrics
            avg_daily_demand = warehouse.current_stock * 0.15 / 30  # TODO: Replace with real forecast
            annual_demand = avg_daily_demand * 365
            safety_stock = warehouse.safety_stock or warehouse.current_stock * 0.1
            
            reorder_point = ReorderService.calculate_reorder_point(
                avg_daily_demand, sku_record.lead_time_days, safety_stock
            )
            
            eoq = ReorderService.calculate_economic_order_quantity(
                annual_demand, sku_record.order_cost, sku_record.holding_cost_per_year
            )
            
            status, days_until_stockout = ReorderService.determine_reorder_status(
                warehouse.current_stock, reorder_point, avg_daily_demand
            )
            
            if status == "URGENT_ORDER_NOW":
                urgent_count += 1
                next_reorder_date = datetime.utcnow()
            elif status == "PLANNED_REORDER":
                planned_count += 1
                days_until_reorder = max(0, int((warehouse.current_stock - reorder_point) / avg_daily_demand)) if avg_daily_demand > 0 else 0
                next_reorder_date = datetime.utcnow() + timedelta(days=days_until_reorder)
            else:
                next_reorder_date = datetime.utcnow() + timedelta(days=30)
            
            detail = ReorderPointDetail(
                sku=warehouse.sku,
                warehouse=warehouse.warehouse,
                current_stock=warehouse.current_stock,
                reorder_point=reorder_point,
                economic_order_quantity=eoq,
                reorder_status=status,
                avg_daily_demand=avg_daily_demand,
                lead_time_days=sku_record.lead_time_days,
                next_reorder_date=next_reorder_date,
                forecasted_demand_next_30days=avg_daily_demand * 30,
                days_until_stockout=days_until_stockout,
                product_name=sku_record.description,
                safety_stock=safety_stock,
            )
            results.append(detail)
            
            # ✅ Batch add
            to_add.append(
                ReorderPointModel(
                    sku=warehouse.sku,
                    warehouse=warehouse.warehouse,
                    avg_daily_demand=avg_daily_demand,
                    lead_time_days=sku_record.lead_time_days,
                    safety_stock=safety_stock,
                    reorder_point_value=reorder_point,
                    economic_order_quantity=eoq,
                    current_stock=warehouse.current_stock,
                    reorder_status=status,
                    days_until_stockout=days_until_stockout,
                )
            )
        
        # ✅ Single commit for all records
        if to_add:
            db.bulk_save_objects(to_add)
            db.commit()
        
        return results, urgent_count, planned_count