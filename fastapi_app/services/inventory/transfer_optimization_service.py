from typing import List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from fastapi_app.models.inventory_model import WarehouseInventory
from fastapi_app.schemas.inventory_schema import InventoryTransferDetail


class TransferOptimizationService:
    """Service for optimizing inventory transfers between warehouses."""

    TRANSFER_COST_PER_UNIT_PER_KM = 0.05  # $0.05 per unit per km (mock)
    WAREHOUSE_DISTANCES = {
        ("WH-01", "WH-02"): 150,
        ("WH-01", "WH-03"): 300,
        ("WH-02", "WH-01"): 150,
        ("WH-02", "WH-03"): 200,
        ("WH-03", "WH-01"): 300,
        ("WH-03", "WH-02"): 200,
    }
    TRANSFER_COST_BASE = 200  # $200 base cost per transfer

    @staticmethod
    def get_distance_between_warehouses(from_wh: str, to_wh: str) -> int:
        """Get distance in km between two warehouses."""
        return TransferOptimizationService.WAREHOUSE_DISTANCES.get((from_wh, to_wh), 100)

    @staticmethod
    def calculate_transfer_cost(
        quantity: float,
        from_warehouse: str,
        to_warehouse: str,
    ) -> float:
        """Calculate cost to transfer inventory between warehouses."""
        distance = TransferOptimizationService.get_distance_between_warehouses(from_warehouse, to_warehouse)
        variable_cost = quantity * distance * TransferOptimizationService.TRANSFER_COST_PER_UNIT_PER_KM
        return TransferOptimizationService.TRANSFER_COST_BASE + variable_cost

    @staticmethod
    def identify_excess_and_shortage(
        db: Session,
    ) -> Tuple[dict, dict]:
        """
        Identify warehouses with excess stock and those with shortage.
        
        Returns:
            Tuple of (excess_by_sku, shortage_by_sku)
        """
        excess_by_sku = {}
        shortage_by_sku = {}

        # Get all warehouse inventory
        all_inventory = db.query(WarehouseInventory).all()

        # Group by SKU
        sku_inventory = {}
        for inv in all_inventory:
            if inv.sku not in sku_inventory:
                sku_inventory[inv.sku] = []
            sku_inventory[inv.sku].append(inv)

        # Identify excess and shortage
        for sku, warehouses in sku_inventory.items():
            total_stock = sum(w.current_stock for w in warehouses)
            avg_per_warehouse = total_stock / len(warehouses) if warehouses else 0

            excess_by_sku[sku] = []
            shortage_by_sku[sku] = []

            for warehouse in warehouses:
                # Excess if current stock > 1.5x average
                if warehouse.current_stock > avg_per_warehouse * 1.5:
                    excess_quantity = warehouse.current_stock - (avg_per_warehouse * 1.2)
                    excess_by_sku[sku].append({
                        "warehouse": warehouse.warehouse,
                        "excess_quantity": excess_quantity,
                        "current_stock": warehouse.current_stock,
                        "region": warehouse.region,
                    })

                # Shortage if current stock < 0.7x average
                if warehouse.current_stock < avg_per_warehouse * 0.7:
                    shortage_quantity = (avg_per_warehouse * 0.8) - warehouse.current_stock
                    shortage_by_sku[sku].append({
                        "warehouse": warehouse.warehouse,
                        "shortage_quantity": shortage_quantity,
                        "current_stock": warehouse.current_stock,
                        "region": warehouse.region,
                    })

        return excess_by_sku, shortage_by_sku

    @staticmethod
    def generate_transfer_recommendations(
        db: Session,
    ) -> Tuple[List[InventoryTransferDetail], float]:
        """
        Generate optimal transfer recommendations.
        
        Returns:
            Tuple of (transfer_list, total_savings)
        """
        excess_by_sku, shortage_by_sku = TransferOptimizationService.identify_excess_and_shortage(db)
        transfers = []
        total_savings = 0.0

        for sku in excess_by_sku:
            if sku not in shortage_by_sku:
                continue

            excess_list = excess_by_sku[sku]
            shortage_list = shortage_by_sku[sku]

            for excess in excess_list:
                for shortage in shortage_list:
                    if excess["warehouse"] == shortage["warehouse"]:
                        continue

                    # Calculate transfer quantity (min of excess and shortage)
                    transfer_qty = min(
                        excess["excess_quantity"],
                        shortage["shortage_quantity"],
                    )

                    # Skip very small transfers
                    if transfer_qty < 5:
                        continue

                    transfer_cost = TransferOptimizationService.calculate_transfer_cost(
                        transfer_qty,
                        excess["warehouse"],
                        shortage["warehouse"],
                    )

                    # Calculate cost savings (reduced carrying cost + stockout prevention)
                    # Mock calculation: $5 per unit per month carrying cost
                    carrying_cost_saved = transfer_qty * 5 * 1  # 1 month savings
                    cost_savings = carrying_cost_saved - transfer_cost

                    if cost_savings > 0:
                        roi = (cost_savings / transfer_cost * 100) if transfer_cost > 0 else 0
                        priority = "high" if roi > 50 else "medium" if roi > 20 else "low"

                        transfer = InventoryTransferDetail(
                            sku=sku,
                            from_warehouse=excess["warehouse"],
                            to_warehouse=shortage["warehouse"],
                            transfer_quantity=transfer_qty,
                            reason="excess_to_shortage",
                            priority=priority,
                            transfer_cost=transfer_cost,
                            cost_savings=cost_savings,
                            roi_percentage=roi,
                            recommended_transfer_date=datetime.utcnow() + timedelta(days=1),
                            expected_days_in_transit=2,
                        )
                        transfers.append(transfer)
                        total_savings += cost_savings

        return transfers, total_savings
