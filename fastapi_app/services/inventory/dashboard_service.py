# fastapi_app/services/inventory/dashboard_service.py
"""
Inventory Dashboard Service - Aggregates all inventory data with statistics.
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from fastapi_app.models.inventory_model import (
    WarehouseInventory,
    InventorySKU,
    InventoryTransfer,
    ExcessStock,
    SlowMovingInventory,
    ReorderPoint,
    InventoryMovement,
)
from fastapi_app.services.inventory.inventory_service import InventoryService
from fastapi_app.services.inventory.transfer_optimization_service import TransferOptimizationService
from fastapi_app.services.inventory.slow_moving_service import SlowMovingService
from fastapi_app.services.inventory.warehouse_analytics_service import WarehouseAnalyticsService


class InventoryDashboardService:
    """Service for inventory dashboard aggregation."""
    
    @staticmethod
    def get_dashboard_data(db: Session) -> Dict[str, Any]:
        """Get all inventory dashboard data in one request."""
        
        # Get health cards
        health = InventoryService.get_inventory_health(db)
        
        # Get reorder points
        reorder_response = InventoryService.get_reorder_points_report(db)
        
        # Get excess stock
        excess_response = InventoryService.get_excess_stock_report(db)
        
        # Get slow moving items
        slow_moving = SlowMovingService.get_slow_moving_items(db)
        
        # Get warehouse distribution
        warehouse_distribution = WarehouseAnalyticsService.get_warehouse_distribution(db)
        
        # Get inventory value distribution
        value_distribution = WarehouseAnalyticsService.get_value_distribution(db)
        
        # Get warehouse summary
        warehouse_summary = WarehouseAnalyticsService.get_warehouse_summary(db)
        
        # Get transfer recommendations
        transfers, total_savings = TransferOptimizationService.generate_transfer_recommendations(db)
        
        # ✅ Enhanced statistics
        stats = InventoryDashboardService._get_dashboard_statistics(db)
        
        return {
            "health_cards": {
                "overall_health": health.health_score,
                "status": health.status,
                "inventory_turnover": health.metrics.stock_turnover_ratio,
                "fill_rate": health.metrics.fill_rate_percentage,
                "stockout_risk_percentage": (health.metrics.stockout_risk_count / max(1, health.total_skus)) * 100,
                "total_skus": health.total_skus,
                "at_risk_skus": health.at_risk_skus,
                "critical_skus": health.critical_skus,
            },
            "statistics": stats,
            "reorder_points": [
                {
                    "product_name": r.product_name or r.sku,
                    "sku": r.sku,
                    "current": r.current_stock,
                    "reorder_point": r.reorder_point,
                    "safety_stock": r.safety_stock,
                    "days_to_stockout": r.days_until_stockout,
                    "status": _map_status(r.reorder_status),
                }
                for r in reorder_response.data[:20]
            ],
            "excess_inventory": [
                {
                    "sku": e.sku,
                    "warehouse": e.warehouse,
                    "current_stock": e.current_stock,
                    "excess_quantity": e.excess_quantity,
                    "days_inventory_on_hand": e.days_inventory_on_hand,
                    "excess_level": e.excess_level,
                    "action": e.action_recommended,
                }
                for e in excess_response.excess_items[:20]
            ],
            "slow_moving_items": [
                {
                    "sku": s.sku,
                    "product_name": s.sku,
                    "turnover_ratio": s.turnover_ratio,
                    "current_stock": s.current_stock,
                    "days_in_stock": s.days_in_stock,
                    "status": s.slow_moving_level,
                    "action": s.action_recommended,
                }
                for s in slow_moving[:20]
            ],
            "warehouse_distribution": warehouse_distribution,
            "inventory_value_distribution": value_distribution,
            "warehouse_summary": warehouse_summary,
            "transfer_recommendations": [
                {
                    "sku": t.sku,
                    "from": t.from_warehouse,
                    "to": t.to_warehouse,
                    "quantity": t.transfer_quantity,
                    "savings": t.cost_savings,
                    "roi": t.roi_percentage,
                    "priority": t.priority,
                    "status": t.status,
                }
                for t in transfers[:10]
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def _get_dashboard_statistics(db: Session) -> Dict[str, Any]:
        """Get dashboard statistics."""
        # Total warehouses
        total_warehouses = db.query(WarehouseInventory.warehouse).distinct().count()
        
        # Total categories
        total_categories = db.query(InventorySKU.category).distinct().count()
        
        # Total inventory value
        total_value = db.query(func.sum(WarehouseInventory.inventory_value)).scalar() or 0
        
        # Average inventory value per warehouse
        avg_value_per_warehouse = total_value / total_warehouses if total_warehouses > 0 else 0
        
        # Fill rate
        total_records = db.query(func.count(WarehouseInventory.id)).scalar() or 0
        filled = db.query(func.count(WarehouseInventory.id)).filter(
            WarehouseInventory.current_stock >= WarehouseInventory.safety_stock
        ).scalar() or 0
        fill_rate = (filled / total_records * 100) if total_records > 0 else 0
        
        # Carrying cost (estimated as 20% of inventory value)
        carrying_cost = total_value * 0.2
        
        # Inventory accuracy (mock - would be calculated from cycle counts)
        inventory_accuracy = 98.5
        
        # Critical counts
        critical_transfers = db.query(func.count(InventoryTransfer.id)).filter(
            InventoryTransfer.status == "pending",
            InventoryTransfer.priority == "high"
        ).scalar() or 0
        
        critical_slow_moving = db.query(func.count(SlowMovingInventory.id)).filter(
            SlowMovingInventory.slow_moving_level == "critical"
        ).scalar() or 0
        
        critical_excess = db.query(func.count(ExcessStock.id)).filter(
            ExcessStock.excess_level == "critical"
        ).scalar() or 0
        
        # Pending reorders
        pending_reorders = db.query(func.count(ReorderPoint.id)).filter(
            ReorderPoint.reorder_status.in_(["URGENT_ORDER_NOW", "PLANNED_REORDER"])
        ).scalar() or 0
        
        # Completed transfers (today)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        completed_transfers_today = db.query(func.count(InventoryTransfer.id)).filter(
            InventoryTransfer.status == "completed",
            InventoryTransfer.completed_at >= today
        ).scalar() or 0
        
        return {
            "total_warehouses": total_warehouses,
            "total_categories": total_categories,
            "total_inventory_value": round(total_value, 2),
            "average_inventory_value_per_warehouse": round(avg_value_per_warehouse, 2),
            "fill_rate": round(fill_rate, 2),
            "carrying_cost": round(carrying_cost, 2),
            "inventory_accuracy": round(inventory_accuracy, 2),
            "critical_transfers": critical_transfers,
            "critical_slow_moving": critical_slow_moving,
            "critical_excess": critical_excess,
            "pending_reorders": pending_reorders,
            "completed_transfers_today": completed_transfers_today,
        }


def _map_status(status: str) -> str:
    """Map internal status to UI-friendly status."""
    status_map = {
        "URGENT_ORDER_NOW": "Critical",
        "PLANNED_REORDER": "Low",
        "SAFE": "Optimal",
    }
    return status_map.get(status, status)