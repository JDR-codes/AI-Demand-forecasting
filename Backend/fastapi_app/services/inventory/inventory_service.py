# fastapi_app/services/inventory/inventory_service.py
"""
Inventory Service - Main service for inventory operations.
"""
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi_app.models.inventory_model import WarehouseInventory
from fastapi_app.services.inventory.reorder_service import ReorderService
from fastapi_app.services.inventory.transfer_optimization_service import TransferOptimizationService
from fastapi_app.services.inventory.excess_stock_service import ExcessStockService
from fastapi_app.services.inventory.slow_moving_service import SlowMovingService
from fastapi_app.services.inventory.warehouse_analytics_service import WarehouseAnalyticsService


class InventoryService:
    """Main service for inventory operations."""
    
    @staticmethod
    def get_inventory_health(db: Session) -> Dict[str, Any]:
        """Get overall inventory health status and metrics."""
        all_inventory = db.query(WarehouseInventory).all()

        if not all_inventory:
            return {
                "health_score": 0,
                "status": "critical",
                "total_skus": 0,
                "at_risk_skus": 0,
                "critical_skus": 0,
                "metrics": {
                    "stock_turnover_ratio": 0,
                    "fill_rate_percentage": 0,
                    "excess_stock_percentage": 0,
                    "stockout_risk_count": 0,
                    "stockout_risk_percentage": 0,
                }
            }

        # Calculate metrics
        total_skus = len(set(inv.sku for inv in all_inventory))
        at_risk_skus = 0
        critical_skus = 0
        stockout_risk_count = 0
        excess_count = 0

        # Analyze each SKU
        sku_groups = {}
        for inv in all_inventory:
            if inv.sku not in sku_groups:
                sku_groups[inv.sku] = []
            sku_groups[inv.sku].append(inv)

        for sku, warehouses in sku_groups.items():
            avg_stock = sum(w.current_stock for w in warehouses) / len(warehouses)

            low_stock_count = sum(1 for w in warehouses if w.current_stock < avg_stock * 0.5)
            high_stock_count = sum(1 for w in warehouses if w.current_stock > avg_stock * 1.5)

            if low_stock_count > 0:
                stockout_risk_count += low_stock_count
                critical_skus += 1
            elif high_stock_count > 0:
                excess_count += 1
                at_risk_skus += 1

        # Calculate stock turnover
        stock_values = [inv.current_stock for inv in all_inventory]
        avg_stock = sum(stock_values) / len(stock_values) if stock_values else 1
        stock_turnover_ratio = max(stock_values) / avg_stock if avg_stock > 0 else 0

        # Calculate fill rate
        filled_count = sum(1 for inv in all_inventory if inv.current_stock >= (inv.safety_stock or inv.current_stock * 0.1))
        fill_rate_percentage = (filled_count / len(all_inventory) * 100) if all_inventory else 0

        # Calculate excess stock percentage
        excess_stock_percentage = (excess_count / total_skus * 100) if total_skus > 0 else 0
        stockout_risk_percentage = (stockout_risk_count / total_skus * 100) if total_skus > 0 else 0

        # Determine health status
        if critical_skus > total_skus * 0.3:
            health_status = "critical"
            health_score = max(0, 50 - (critical_skus - total_skus * 0.3) * 20)
        elif at_risk_skus > total_skus * 0.15:
            health_status = "at_risk"
            health_score = 60 + (fill_rate_percentage - 70)
        else:
            health_status = "healthy"
            health_score = min(100, 80 + (fill_rate_percentage - 85))

        return {
            "health_score": round(max(0, min(100, health_score)), 1),
            "status": health_status,
            "total_skus": total_skus,
            "at_risk_skus": at_risk_skus,
            "critical_skus": critical_skus,
            "metrics": {
                "stock_turnover_ratio": round(stock_turnover_ratio, 2),
                "fill_rate_percentage": round(fill_rate_percentage, 1),
                "excess_stock_percentage": round(excess_stock_percentage, 1),
                "stockout_risk_count": stockout_risk_count,
                "stockout_risk_percentage": round(stockout_risk_percentage, 1),
            }
        }

    @staticmethod
    def get_reorder_points_report(db: Session) -> Dict[str, Any]:
        """Get reorder point recommendations for dashboard."""
        return ReorderService.batch_calculate_reorder_points(db)

    @staticmethod
    def get_transfer_recommendations(db: Session) -> List[Dict[str, Any]]:
        """Get optimal inventory transfer recommendations."""
        return TransferOptimizationService.generate_transfer_recommendations(db)

    @staticmethod
    def get_excess_stock_report(db: Session) -> Dict[str, Any]:
        """Get excess inventory analysis and recommendations."""
        return ExcessStockService.identify_excess_stock(db)
    
    @staticmethod
    def get_slow_moving_items(db: Session) -> List[Dict[str, Any]]:
        """Get slow-moving inventory items."""
        return SlowMovingService.get_slow_moving_items(db)
    
    @staticmethod
    def get_warehouse_distribution(db: Session) -> List[Dict[str, Any]]:
        """Get warehouse units distribution."""
        return WarehouseAnalyticsService.get_warehouse_distribution(db)
    
    @staticmethod
    def get_value_distribution(db: Session) -> List[Dict[str, Any]]:
        """Get inventory value distribution."""
        return WarehouseAnalyticsService.get_value_distribution(db)
    
    @staticmethod
    def get_warehouse_summary(db: Session) -> List[Dict[str, Any]]:
        """Get warehouse summary."""
        return WarehouseAnalyticsService.get_warehouse_summary(db)