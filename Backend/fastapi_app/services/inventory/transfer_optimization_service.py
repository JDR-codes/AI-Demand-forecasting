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

    @staticmethod
    def approve_transfer(db: Session, transfer_id: int) -> Dict[str, Any]:
        """Approve and execute a pending transfer, adjusting stock levels."""
        transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
        if not transfer:
            return {"error": "Transfer recommendation not found"}
        if transfer.status != "pending":
            return {"error": f"Transfer is already {transfer.status}"}
            
        # Locate source inventory
        source_inv = db.query(WarehouseInventory).filter_by(
            sku=transfer.sku,
            warehouse=transfer.from_warehouse
        ).first()
        
        # Locate target inventory
        target_inv = db.query(WarehouseInventory).filter_by(
            sku=transfer.sku,
            warehouse=transfer.to_warehouse
        ).first()
        
        if not source_inv:
            return {"error": f"Source inventory not found for SKU {transfer.sku} in {transfer.from_warehouse}"}
            
        if source_inv.current_stock < transfer.transfer_quantity:
            return {"error": f"Insufficient stock in source warehouse {transfer.from_warehouse}. Current stock: {source_inv.current_stock}"}
            
        # Deduct from source
        source_inv.current_stock = round(source_inv.current_stock - transfer.transfer_quantity, 2)
        source_inv.inventory_value = round(source_inv.current_stock * (source_inv.inventory_sku.unit_cost if source_inv.inventory_sku else 0), 2)
        
        # Add to target
        if not target_inv:
            target_inv = WarehouseInventory(
                sku=transfer.sku,
                warehouse=transfer.to_warehouse,
                region=source_inv.region or "Default",
                current_stock=0.0,
                safety_stock=source_inv.safety_stock,
                reorder_point=source_inv.reorder_point,
                inventory_value=0.0
            )
            db.add(target_inv)
            db.flush()
            
        target_inv.current_stock = round(target_inv.current_stock + transfer.transfer_quantity, 2)
        target_inv.inventory_value = round(target_inv.current_stock * (target_inv.inventory_sku.unit_cost if target_inv.inventory_sku else 0), 2)
        
        # Update transfer record
        transfer.status = "completed"
        db.commit()
        
        return {
            "success": True,
            "transfer_id": transfer.id,
            "sku": transfer.sku,
            "from_warehouse": transfer.from_warehouse,
            "to_warehouse": transfer.to_warehouse,
            "quantity": transfer.transfer_quantity,
            "status": "completed"
        }

    @staticmethod
    def create_manual_transfer(
        db: Session,
        sku: str,
        from_warehouse: str,
        to_warehouse: str,
        quantity: float,
        priority: str
    ) -> Dict[str, Any]:
        """Create and immediately execute a manual transfer."""
        sku_record = db.query(InventorySKU).filter(InventorySKU.sku == sku).first()
        if not sku_record:
            return {"error": f"SKU {sku} not found"}
            
        transfer = InventoryTransfer(
            sku=sku,
            from_warehouse=from_warehouse,
            to_warehouse=to_warehouse,
            transfer_quantity=quantity,
            priority=priority,
            status="pending"
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        
        return TransferOptimizationService.approve_transfer(db, transfer.id)

    @staticmethod
    def get_transfers(db: Session, status: str = None) -> List[InventoryTransfer]:
        """List all transfer history."""
        query = db.query(InventoryTransfer)
        if status:
            query = query.filter(InventoryTransfer.status == status)
        return query.order_by(InventoryTransfer.created_at.desc()).all()