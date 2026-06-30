import math
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from fastapi_app.models.inventory_model import (
    InventorySKU,
    WarehouseInventory,
    ReorderPoint as ReorderPointModel,
)
from fastapi_app.schemas.inventory_schema import ReorderPointDetail


class ReorderService:
    """Service for calculating reorder points and economic order quantities."""

    @staticmethod
    def calculate_economic_order_quantity(
        annual_demand: float,
        order_cost: float,
        holding_cost: float,
    ) -> float:
        """
        Calculate EOQ using formula: EOQ = √(2DS/H)
        
        Args:
            annual_demand: Total annual demand
            order_cost: Cost to place one order
            holding_cost: Annual holding/carrying cost per unit
        
        Returns:
            Economic order quantity
        """
        if holding_cost <= 0:
            return 0
        eoq = math.sqrt((2 * annual_demand * order_cost) / holding_cost)
        return eoq

    @staticmethod
    def calculate_reorder_point(
        avg_daily_demand: float,
        lead_time_days: int,
        safety_stock: float,
    ) -> float:
        """
        Calculate reorder point using formula: ROP = (Avg Daily Demand × Lead Time) + Safety Stock
        
        Args:
            avg_daily_demand: Average daily demand
            lead_time_days: Lead time in days
            safety_stock: Calculated safety stock
        
        Returns:
            Reorder point quantity
        """
        return (avg_daily_demand * lead_time_days) + safety_stock

    @staticmethod
    def determine_reorder_status(
        current_stock: float,
        reorder_point: float,
        avg_daily_demand: float,
    ) -> Tuple[str, Optional[int]]:
        """
        Determine reorder status and days until stockout.
        
        Args:
            current_stock: Current inventory level
            reorder_point: Calculated reorder point
            avg_daily_demand: Average daily demand
        
        Returns:
            Tuple of (status, days_until_stockout)
        """
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
    def get_reorder_point_for_sku(
        db: Session,
        sku: str,
        warehouse: str,
        current_stock: float,
        avg_daily_demand: float,
        safety_stock: float,
        lead_time_days: int,
        annual_demand: float,
    ) -> ReorderPointDetail:
        """Calculate and return reorder point for a SKU."""
        # Get SKU details for EOQ calculation
        sku_record = db.query(InventorySKU).filter_by(sku=sku).first()
        
        if not sku_record:
            # Use default values if SKU not found
            order_cost = 50.0
            holding_cost = 5.0
        else:
            order_cost = sku_record.order_cost
            holding_cost = sku_record.holding_cost_per_year

        reorder_point = ReorderService.calculate_reorder_point(
            avg_daily_demand, lead_time_days, safety_stock
        )
        
        eoq = ReorderService.calculate_economic_order_quantity(
            annual_demand, order_cost, holding_cost
        )

        status, days_until_stockout = ReorderService.determine_reorder_status(
            current_stock, reorder_point, avg_daily_demand
        )

        # Calculate next reorder date based on status
        if status == "URGENT_ORDER_NOW":
            next_reorder_date = datetime.utcnow()
        else:
            days_until_reorder = max(0, int((current_stock - reorder_point) / avg_daily_demand)) if avg_daily_demand > 0 else 0
            next_reorder_date = datetime.utcnow() + timedelta(days=days_until_reorder)

        forecasted_demand_30days = avg_daily_demand * 30

        return ReorderPointDetail(
            sku=sku,
            warehouse=warehouse,
            current_stock=current_stock,
            reorder_point=reorder_point,
            economic_order_quantity=eoq,
            reorder_status=status,
            avg_daily_demand=avg_daily_demand,
            lead_time_days=lead_time_days,
            next_reorder_date=next_reorder_date,
            forecasted_demand_next_30days=forecasted_demand_30days,
            days_until_stockout=days_until_stockout,
        )

    @staticmethod
    def batch_calculate_reorder_points(
        db: Session,
        sku_list: List[str],
    ) -> Tuple[List[ReorderPointDetail], int, int]:
        """Calculate reorder points for multiple SKUs."""
        urgent_count = 0
        planned_count = 0
        results = []

        for sku in sku_list:
            warehouses = db.query(WarehouseInventory).filter_by(sku=sku).all()
            sku_record = db.query(InventorySKU).filter_by(sku=sku).first()

            if not sku_record:
                continue

            for warehouse_record in warehouses:
                # Mock avg_daily_demand - in production, calculate from historical data
                avg_daily_demand = warehouse_record.current_stock * 0.15 / 30  # 15% of stock per month
                annual_demand = avg_daily_demand * 365
                safety_stock = warehouse_record.safety_stock or warehouse_record.current_stock * 0.1

                detail = ReorderService.get_reorder_point_for_sku(
                    db,
                    sku,
                    warehouse_record.warehouse,
                    warehouse_record.current_stock,
                    avg_daily_demand,
                    safety_stock,
                    sku_record.lead_time_days,
                    annual_demand,
                )

                if detail.reorder_status == "URGENT_ORDER_NOW":
                    urgent_count += 1
                elif detail.reorder_status == "PLANNED_REORDER":
                    planned_count += 1

                results.append(detail)

        return results, urgent_count, planned_count
