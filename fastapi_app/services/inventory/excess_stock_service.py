from typing import List, Tuple
from sqlalchemy.orm import Session

from fastapi_app.models.inventory_model import WarehouseInventory
from fastapi_app.schemas.inventory_schema import ExcessStockDetail


class ExcessStockService:
    """Service for identifying and managing excess inventory."""

    EXCESS_LEVEL_THRESHOLDS = {
        "critical": 120,  # >120 days of inventory on hand
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
    def recommend_action(
        excess_level: str,
        days_inventory_on_hand: float,
    ) -> str:
        """Recommend action based on excess level."""
        if excess_level == "critical":
            return "aggressive_discount"
        elif excess_level == "high":
            return "discount"
        elif excess_level == "medium":
            return "transfer"
        else:
            return "monitor"

    @staticmethod
    def calculate_storage_risk_score(
        days_inventory_on_hand: float,
        excess_quantity: float,
        current_stock: float,
    ) -> float:
        """
        Calculate storage risk score (0-100).
        Higher score = higher risk.
        """
        # Component 1: Days of inventory (0-50 points)
        days_component = min(50, (days_inventory_on_hand / 180) * 50)

        # Component 2: Excess percentage (0-30 points)
        excess_percentage = (excess_quantity / current_stock * 100) if current_stock > 0 else 0
        excess_component = min(30, (excess_percentage / 100) * 30)

        # Component 3: Obsolescence risk (0-20 points) - mock
        obsolescence_component = 10

        risk_score = days_component + excess_component + obsolescence_component
        return min(100, risk_score)

    @staticmethod
    def identify_excess_stock(
        db: Session,
    ) -> Tuple[List[ExcessStockDetail], float, float, float]:
        """
        Identify all excess stock in the network.
        
        Returns:
            Tuple of (excess_items, total_excess_qty, total_carrying_cost, total_potential_savings)
        """
        excess_items = []
        total_excess_quantity = 0.0
        total_carrying_cost = 0.0
        total_potential_savings = 0.0

        all_inventory = db.query(WarehouseInventory).all()

        for warehouse_inv in all_inventory:
            # Mock forecasted demand - in production, use actual forecast data
            forecasted_demand_30days = warehouse_inv.current_stock * 0.15  # 15% of current stock

            # Calculate excess quantity
            min_safe_level = warehouse_inv.safety_stock or warehouse_inv.current_stock * 0.1
            excess_quantity = max(
                0,
                warehouse_inv.current_stock - forecasted_demand_30days - min_safe_level,
            )

            if excess_quantity <= 0:
                continue

            # Calculate days inventory on hand
            days_inventory_on_hand = (warehouse_inv.current_stock / forecasted_demand_30days * 30) if forecasted_demand_30days > 0 else 0

            # Skip if not excessive
            if days_inventory_on_hand < ExcessStockService.EXCESS_LEVEL_THRESHOLDS["low"]:
                continue

            # Mock carrying cost per unit yearly - in production, use actual costs
            carrying_cost_per_unit_yearly = warehouse_inv.current_stock * 0.05

            total_carrying_cost_item = excess_quantity * carrying_cost_per_unit_yearly

            excess_level = ExcessStockService.determine_excess_level(days_inventory_on_hand)
            action = ExcessStockService.recommend_action(excess_level, days_inventory_on_hand)

            # Calculate liquidation value (mock: 50% of carrying cost)
            estimated_liquidation_value = excess_quantity * (carrying_cost_per_unit_yearly * 0.5)

            potential_savings = total_carrying_cost_item - estimated_liquidation_value

            storage_risk_score = ExcessStockService.calculate_storage_risk_score(
                days_inventory_on_hand,
                excess_quantity,
                warehouse_inv.current_stock,
            )

            excess_detail = ExcessStockDetail(
                sku=warehouse_inv.sku,
                warehouse=warehouse_inv.warehouse,
                region=warehouse_inv.region,
                current_stock=warehouse_inv.current_stock,
                forecasted_demand_30days=forecasted_demand_30days,
                days_inventory_on_hand=days_inventory_on_hand,
                excess_quantity=excess_quantity,
                carrying_cost_per_unit_yearly=carrying_cost_per_unit_yearly,
                total_carrying_cost=total_carrying_cost_item,
                excess_level=excess_level,
                action_recommended=action,
                estimated_liquidation_value=estimated_liquidation_value,
                potential_savings=potential_savings,
                storage_risk_score=storage_risk_score,
            )

            excess_items.append(excess_detail)
            total_excess_quantity += excess_quantity
            total_carrying_cost += total_carrying_cost_item
            total_potential_savings += potential_savings

        return excess_items, total_excess_quantity, total_carrying_cost, total_potential_savings
