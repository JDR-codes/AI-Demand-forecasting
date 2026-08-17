# fastapi_app/services/inventory/dashboard_service.py
"""
Inventory Dashboard Service - Aggregates all inventory data for dashboard.
"""
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from fastapi_app.services.inventory.inventory_service import InventoryService


class InventoryDashboardService:
    """Service for inventory dashboard aggregation."""
    
    @staticmethod
    def get_dashboard_data(db: Session) -> Dict[str, Any]:
        """Get all inventory dashboard data in one request."""
        
        # Get health cards
        health = InventoryService.get_inventory_health(db)
        
        # Get reorder points
        reorder_data = InventoryService.get_reorder_points_report(db)
        
        # Get excess stock
        excess_data = InventoryService.get_excess_stock_report(db)
        
        # Get slow moving items
        slow_moving = InventoryService.get_slow_moving_items(db)
        
        # Get warehouse distribution
        warehouse_distribution = InventoryService.get_warehouse_distribution(db)
        
        # Get inventory value distribution
        value_distribution = InventoryService.get_value_distribution(db)
        
        # Get warehouse summary
        warehouse_summary = InventoryService.get_warehouse_summary(db)
        
        # Get transfer recommendations
        transfers = InventoryService.get_transfer_recommendations(db)
        
        return {
            "health_cards": {
                "overall_health": health["health_score"],
                "status": health["status"],
                "inventory_turnover": health["metrics"]["stock_turnover_ratio"],
                "fill_rate": health["metrics"]["fill_rate_percentage"],
                "stockout_risk_percentage": health["metrics"]["stockout_risk_percentage"],
                "total_skus": health["total_skus"],
                "at_risk_skus": health["at_risk_skus"],
                "critical_skus": health["critical_skus"],
            },
            "reorder_points": reorder_data["data"],
            "excess_inventory": excess_data["excess_items"],
            "slow_moving_items": slow_moving,
            "warehouse_distribution": warehouse_distribution,
            "inventory_value_distribution": value_distribution,
            "warehouse_summary": warehouse_summary,
            "transfer_recommendations": transfers,
            "timestamp": datetime.utcnow().isoformat(),
        }