# fastapi_app/services/inventory/inventory_service.py
from typing import Any, Dict, List
from sqlalchemy.orm import Session, joinedload

from fastapi_app.models.inventory_model import (
    InventorySKU,
    SlowMovingInventory,
    WarehouseInventory,
)
from fastapi_app.schemas.inventory_schema import (
    InventoryHealthResponse,
    InventoryHealthMetrics,
    SafetyStockResponse,
    ReorderPointResponse,
    TransferOptimizationResponse,
    ExcessStockResponse,
    SlowMovingItemResponse,
)
from fastapi_app.services.inventory.safety_stock_service import SafetyStockService
from fastapi_app.services.inventory.reorder_service import ReorderService
from fastapi_app.services.inventory.transfer_optimization_service import TransferOptimizationService
from fastapi_app.services.inventory.excess_stock_service import ExcessStockService
from fastapi_app.services.inventory.slow_moving_service import SlowMovingService
from fastapi_app.services.inventory.warehouse_analytics_service import WarehouseAnalyticsService


class InventoryService:
    """Main service for inventory optimization."""
    
    @staticmethod
    def get_inventory_health(db: Session) -> InventoryHealthResponse:
        """Get overall inventory health status and metrics."""
        all_inventory = db.query(WarehouseInventory).all()

        if not all_inventory:
            return InventoryHealthResponse(
                health_score=0,
                status="critical",
                total_skus=0,
                at_risk_skus=0,
                critical_skus=0,
                metrics=InventoryHealthMetrics(
                    stock_turnover_ratio=0,
                    fill_rate_percentage=0,
                    excess_stock_percentage=0,
                    stockout_risk_count=0,
                ),
            )

        # Calculate metrics
        total_skus = len(set(inv.sku for inv in all_inventory))
        at_risk_skus = 0
        critical_skus = 0
        total_stock = sum(inv.current_stock for inv in all_inventory)
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

        metrics = InventoryHealthMetrics(
            stock_turnover_ratio=round(stock_turnover_ratio, 2),
            fill_rate_percentage=round(fill_rate_percentage, 1),
            excess_stock_percentage=round(excess_stock_percentage, 1),
            stockout_risk_count=stockout_risk_count,
        )

        return InventoryHealthResponse(
            health_score=round(max(0, min(100, health_score)), 1),
            status=health_status,
            total_skus=total_skus,
            at_risk_skus=at_risk_skus,
            critical_skus=critical_skus,
            metrics=metrics,
        )

    @staticmethod
    def get_safety_stock_report(
        db: Session,
        service_level: float = 95,
    ) -> SafetyStockResponse:
        """Get safety stock recommendations for all SKUs."""
        all_inventory = db.query(WarehouseInventory).all()

        if not all_inventory:
            return SafetyStockResponse(data=[], summary={"avg_variance": 0, "total_understock_risk": 0})

        sku_list = list(set(inv.sku for inv in all_inventory))
        safety_stock_details = SafetyStockService.batch_calculate_safety_stock(db, sku_list, service_level)

        understock_risk = sum(1 for detail in safety_stock_details if detail.status == "below_target")
        avg_variance = sum(detail.variance_percentage for detail in safety_stock_details) / len(safety_stock_details) if safety_stock_details else 0

        summary = {
            "avg_variance": round(avg_variance, 2),
            "total_understock_risk": understock_risk,
        }

        return SafetyStockResponse(data=safety_stock_details, summary=summary)

    @staticmethod
    def get_reorder_points_report(db: Session) -> ReorderPointResponse:
        """Get reorder point recommendations for all SKUs."""
        all_inventory = db.query(WarehouseInventory).all()

        if not all_inventory:
            return ReorderPointResponse(data=[], total_urgent_reorders=0, total_planned_reorders=0)

        sku_list = list(set(inv.sku for inv in all_inventory))
        reorder_details, urgent_count, planned_count = ReorderService.batch_calculate_reorder_points(db, sku_list)

        return ReorderPointResponse(
            data=reorder_details,
            total_urgent_reorders=urgent_count,
            total_planned_reorders=planned_count,
        )

    @staticmethod
    def get_transfer_recommendations(db: Session) -> TransferOptimizationResponse:
        """Get optimal inventory transfer recommendations."""
        transfers, total_savings = TransferOptimizationService.generate_transfer_recommendations(db)

        return TransferOptimizationResponse(
            transfers=transfers,
            total_transfers_recommended=len(transfers),
            total_potential_savings=round(total_savings, 2),
        )

    @staticmethod
    def get_excess_stock_report(db: Session) -> ExcessStockResponse:
        """Get excess inventory analysis and recommendations."""
        excess_items, total_excess_qty, total_carrying_cost, total_savings = ExcessStockService.identify_excess_stock(db)

        return ExcessStockResponse(
            excess_items=excess_items,
            total_excess_quantity=round(total_excess_qty, 2),
            total_carrying_cost=round(total_carrying_cost, 2),
            total_potential_savings=round(total_savings, 2),
        )
    
    @staticmethod
    def get_slow_moving_items(db: Session) -> List[SlowMovingItemResponse]:
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
    
    @staticmethod
    def search_inventory(db: Session, search: str, limit: int = 50, offset: int = 0):
        """Search inventory by SKU, product, warehouse, category, region."""
        from sqlalchemy import or_
        
        query = db.query(WarehouseInventory).join(InventorySKU, WarehouseInventory.sku == InventorySKU.sku)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    WarehouseInventory.sku.ilike(search_term),
                    InventorySKU.description.ilike(search_term),
                    WarehouseInventory.warehouse.ilike(search_term),
                    InventorySKU.category.ilike(search_term),
                    WarehouseInventory.region.ilike(search_term),
                )
            )
        
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "pages": (total + limit - 1) // limit if limit > 0 and total > 0 else 1,
            "items": [
                {
                    "sku": i.sku,
                    "warehouse": i.warehouse,
                    "region": i.region,
                    "current_stock": i.current_stock,
                    "safety_stock": i.safety_stock,
                    "reorder_point": i.reorder_point,
                }
                for i in items
            ]
        }

    @staticmethod
    def seed_sample_inventory(db: Session):
        """Seed database with enhanced sample inventory data."""
        # Clear existing data
        db.query(WarehouseInventory).delete()
        db.query(InventorySKU).delete()
        db.query(SlowMovingInventory).delete()
        db.commit()

        # Create sample SKUs - 20 per category
        categories = ["Electronics", "Furniture", "Accessories", "Grocery", "Fashion"]
        skus = []
        
        for category in categories:
            for i in range(1, 21):
                sku = InventorySKU(
                    sku=f"SKU-{category[:3].upper()}-{i:03d}",
                    description=f"{category} Product {i}",
                    category=category,
                    unit_cost=10 + (i * 5),
                    holding_cost_per_year=2 + (i * 0.5),
                    order_cost=30 + (i * 2),
                    lead_time_days=3 + (i % 7),
                    min_order_quantity=i * 5,
                )
                skus.append(sku)
        
        db.add_all(skus)
        db.commit()

        # Create sample warehouse inventory across 3 warehouses
        warehouses = ["WH-01", "WH-02", "WH-03"]
        regions = ["North", "South", "East"]
        warehouse_inventory = []
        
        for sku in skus:
            base_stock = 100 + (hash(sku.sku) % 500)
            for i, warehouse in enumerate(warehouses):
                variance = 0.8 + (i * 0.2)
                stock = base_stock * variance
                
                inv = WarehouseInventory(
                    sku=sku.sku,
                    warehouse=warehouse,
                    region=regions[i],
                    current_stock=round(stock, 2),
                    safety_stock=round(stock * 0.1, 2),
                    reorder_point=round(stock * 0.2, 2),
                )
                warehouse_inventory.append(inv)
        
        db.add_all(warehouse_inventory)
        db.commit()
        
    @staticmethod
    def update_inventory_value(db: Session):
        """Update inventory_value for all warehouse records."""
        warehouses = db.query(WarehouseInventory).options(
            joinedload(WarehouseInventory.inventory_sku)
        ).all()
        
        for warehouse in warehouses:
            sku = warehouse.inventory_sku
            if sku:
                warehouse.inventory_value = warehouse.current_stock * sku.unit_cost
            else:
                warehouse.inventory_value = 0
        
        db.commit()
