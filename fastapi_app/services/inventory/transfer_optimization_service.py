#fastapi_app/services/inventory/transfer_optimization_service.py
"""
Transfer Optimization Service - Generates transfer recommendations.
"""
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session

from fastapi_app.models.inventory_model import WarehouseInventory, InventorySKU, InventoryTransfer


class TransferOptimizationService:
    """Service for optimizing inventory transfers."""
    
    @staticmethod
    def generate_transfer_recommendations(db: Session) -> List[Dict[str, Any]]:
        """Generate optimal transfer recommendations."""
        excess_by_sku, shortage_by_sku = TransferOptimizationService._identify_excess_and_shortage(db)
        transfers = []

        for sku in excess_by_sku:
            if sku not in shortage_by_sku:
                continue

            excess_list = excess_by_sku[sku]
            shortage_list = shortage_by_sku[sku]
            
            sku_record = db.query(InventorySKU).filter(InventorySKU.sku == sku).first()
            product_name = sku_record.description if sku_record else sku

            for excess in excess_list:
                for shortage in shortage_list:
                    if excess["warehouse"] == shortage["warehouse"]:
                        continue

                    transfer_qty = min(excess["excess_quantity"], shortage["shortage_quantity"])

                    if transfer_qty < 5:
                        continue

                    # Determine priority
                    if transfer_qty > 100:
                        priority = "high"
                    elif transfer_qty > 50:
                        priority = "medium"
                    else:
                        priority = "low"

                    # Persist transfer
                    transfer = InventoryTransfer(
                        sku=sku,
                        from_warehouse=excess["warehouse"],
                        to_warehouse=shortage["warehouse"],
                        transfer_quantity=transfer_qty,
                        priority=priority,
                        status="pending",
                    )
                    db.add(transfer)

                    transfers.append({
                        "sku": sku,
                        "product_name": product_name,
                        "quantity": transfer_qty,
                        "from_warehouse": excess["warehouse"],
                        "to_warehouse": shortage["warehouse"],
                        "priority": priority,
                        "status": "pending",
                    })

        db.commit()
        return transfers

    @staticmethod
    def _identify_excess_and_shortage(db: Session) -> Tuple[Dict, Dict]:
        """Identify warehouses with excess stock and those with shortage."""
        excess_by_sku = {}
        shortage_by_sku = {}

        all_inventory = db.query(WarehouseInventory).all()

        sku_inventory = {}
        for inv in all_inventory:
            if inv.sku not in sku_inventory:
                sku_inventory[inv.sku] = []
            sku_inventory[inv.sku].append(inv)

        for sku, warehouses in sku_inventory.items():
            total_stock = sum(w.current_stock for w in warehouses)
            avg_per_warehouse = total_stock / len(warehouses) if warehouses else 0

            excess_by_sku[sku] = []
            shortage_by_sku[sku] = []

            for warehouse in warehouses:
                if warehouse.current_stock > avg_per_warehouse * 1.5:
                    excess_quantity = warehouse.current_stock - (avg_per_warehouse * 1.2)
                    excess_by_sku[sku].append({
                        "warehouse": warehouse.warehouse,
                        "excess_quantity": excess_quantity,
                    })

                if warehouse.current_stock < avg_per_warehouse * 0.7:
                    shortage_quantity = (avg_per_warehouse * 0.8) - warehouse.current_stock
                    shortage_by_sku[sku].append({
                        "warehouse": warehouse.warehouse,
                        "shortage_quantity": shortage_quantity,
                    })

        return excess_by_sku, shortage_by_sku