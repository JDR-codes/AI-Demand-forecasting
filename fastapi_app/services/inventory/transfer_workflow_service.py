# fastapi_app/services/inventory/transfer_workflow_service.py
"""
Transfer Workflow Service - Manages the complete transfer lifecycle.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import logging

from fastapi_app.models.inventory_model import InventoryTransfer, WarehouseInventory
from fastapi_app.services.inventory.history_service import InventoryHistoryService
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.inventory.alert_service import AlertService

logger = logging.getLogger(__name__)


class TransferWorkflowService:
    """Service for managing transfer workflow states."""
    
    VALID_TRANSITIONS = {
        "pending": ["approved", "rejected", "cancelled"],
        "approved": ["picking", "cancelled"],
        "picking": ["packed", "cancelled"],
        "packed": ["dispatched", "cancelled"],
        "dispatched": ["in_transit", "cancelled"],
        "in_transit": ["received", "cancelled"],
        "received": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
        "rejected": [],
    }
    
    @staticmethod
    def _validate_transition(current_status: str, new_status: str) -> bool:
        """Validate if a status transition is allowed."""
        return new_status in TransferWorkflowService.VALID_TRANSITIONS.get(current_status, [])
    
    @staticmethod
    def _update_transfer_status(
        db: Session,
        transfer: InventoryTransfer,
        new_status: str,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> InventoryTransfer:
        """Update transfer status with audit trail."""
        old_status = transfer.status
        transfer.status = new_status
        transfer.updated_at = datetime.utcnow()
        
        # Update specific fields based on status
        if new_status == "approved":
            transfer.approved_by = str(user_id) if user_id else None
            transfer.approval_status = "approved"
        elif new_status == "completed":
            transfer.completed_at = datetime.utcnow()
            transfer.completed_by = str(user_id) if user_id else None
        elif new_status == "dispatched":
            transfer.expected_arrival = datetime.utcnow() + timedelta(days=transfer.expected_days_in_transit or 2)
        
        # Generate transfer number if not exists
        if not transfer.transfer_number:
            transfer.transfer_number = f"TRF-{datetime.utcnow().strftime('%Y%m%d')}-{transfer.id:04d}"
        
        db.commit()
        db.refresh(transfer)
        
        # Record history
        InventoryHistoryService.record_history(
            db=db,
            sku=transfer.sku,
            warehouse=transfer.from_warehouse,
            old_stock=0,
            new_stock=0,
            reason=f"transfer_{new_status}",
            reference=transfer.transfer_number,
            user_id=user_id,
        )
        
        # Check alerts for the affected SKU
        AlertService.check_and_create_alerts(
            db=db,
            sku=transfer.sku,
            warehouse=transfer.to_warehouse,
            current_stock=0
        )
        
        return transfer
    
    @staticmethod
    async def _send_notification(
        user_id: int,
        title: str,
        message: str,
        priority: str = "info"
    ):
        """Send notification via WebSocket and database."""
        from fastapi_app.db.session import SessionLocal
        db = SessionLocal()
        try:
            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                title=title,
                message=message,
                notification_type="inventory",
                priority=priority
            )
            await manager.send_notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type="inventory",
                priority=priority
            )
        finally:
            db.close()
    
    @staticmethod
    def approve_transfer(
        db: Session,
        transfer_id: int,
        user_id: int,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve a pending transfer."""
        transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
        if not transfer:
            return {"error": "Transfer not found"}
        
        if not TransferWorkflowService._validate_transition(transfer.status, "approved"):
            return {"error": f"Cannot approve transfer with status: {transfer.status}"}
        
        updated = TransferWorkflowService._update_transfer_status(db, transfer, "approved", user_id, notes)
        
        # Send notification
        import asyncio
        asyncio.create_task(
            TransferWorkflowService._send_notification(
                user_id=user_id,
                title=f"✅ Transfer Approved: {transfer.transfer_number or transfer.id}",
                message=f"Transfer of {transfer.transfer_quantity} units of {transfer.sku} from {transfer.from_warehouse} to {transfer.to_warehouse} has been approved.",
                priority="success"
            )
        )
        
        return {"success": True, "transfer": updated}
    
    @staticmethod
    def reject_transfer(
        db: Session,
        transfer_id: int,
        user_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """Reject a pending transfer."""
        transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
        if not transfer:
            return {"error": "Transfer not found"}
        
        if not TransferWorkflowService._validate_transition(transfer.status, "rejected"):
            return {"error": f"Cannot reject transfer with status: {transfer.status}"}
        
        updated = TransferWorkflowService._update_transfer_status(db, transfer, "rejected", user_id)
        
        import asyncio
        asyncio.create_task(
            TransferWorkflowService._send_notification(
                user_id=user_id,
                title=f"❌ Transfer Rejected: {transfer.transfer_number or transfer.id}",
                message=f"Transfer of {transfer.transfer_quantity} units of {transfer.sku} was rejected. Reason: {reason}",
                priority="error"
            )
        )
        
        return {"success": True, "transfer": updated}
    
    @staticmethod
    def dispatch_transfer(
        db: Session,
        transfer_id: int,
        user_id: int,
        vehicle: Optional[str] = None,
        driver: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch a transfer."""
        transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
        if not transfer:
            return {"error": "Transfer not found"}
        
        if not TransferWorkflowService._validate_transition(transfer.status, "dispatched"):
            return {"error": f"Cannot dispatch transfer with status: {transfer.status}"}
        
        transfer.vehicle = vehicle
        transfer.driver = driver
        transfer.tracking_number = tracking_number
        
        updated = TransferWorkflowService._update_transfer_status(db, transfer, "dispatched", user_id)
        
        import asyncio
        asyncio.create_task(
            TransferWorkflowService._send_notification(
                user_id=user_id,
                title=f"🚚 Transfer Dispatched: {transfer.transfer_number or transfer.id}",
                message=f"Transfer of {transfer.transfer_quantity} units of {transfer.sku} has been dispatched. Expected arrival: {transfer.expected_arrival}",
                priority="info"
            )
        )
        
        return {"success": True, "transfer": updated}
    
    @staticmethod
    def receive_transfer(
        db: Session,
        transfer_id: int,
        user_id: int,
        actual_quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Receive a transfer at destination."""
        transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
        if not transfer:
            return {"error": "Transfer not found"}
        
        if not TransferWorkflowService._validate_transition(transfer.status, "received"):
            return {"error": f"Cannot receive transfer with status: {transfer.status}"}
        
        quantity = actual_quantity or transfer.transfer_quantity
        
        # Update destination warehouse stock
        dest_inventory = db.query(WarehouseInventory).filter(
            WarehouseInventory.sku == transfer.sku,
            WarehouseInventory.warehouse == transfer.to_warehouse
        ).first()
        
        if dest_inventory:
            old_stock = dest_inventory.current_stock
            dest_inventory.current_stock += quantity
            dest_inventory.inventory_value = dest_inventory.current_stock * (dest_inventory.inventory_value / dest_inventory.current_stock if dest_inventory.current_stock > 0 else 0)
            db.commit()
            
            # Record history
            InventoryHistoryService.record_history(
                db=db,
                sku=transfer.sku,
                warehouse=transfer.to_warehouse,
                old_stock=old_stock,
                new_stock=dest_inventory.current_stock,
                reason="transfer_received",
                reference=transfer.transfer_number,
                user_id=user_id,
            )
            
            # Check alerts
            AlertService.check_and_create_alerts(
                db=db,
                sku=transfer.sku,
                warehouse=transfer.to_warehouse,
                current_stock=dest_inventory.current_stock
            )
        
        # Update source warehouse stock
        source_inventory = db.query(WarehouseInventory).filter(
            WarehouseInventory.sku == transfer.sku,
            WarehouseInventory.warehouse == transfer.from_warehouse
        ).first()
        
        if source_inventory:
            old_stock = source_inventory.current_stock
            source_inventory.current_stock -= quantity
            source_inventory.inventory_value = source_inventory.current_stock * (source_inventory.inventory_value / source_inventory.current_stock if source_inventory.current_stock > 0 else 0)
            db.commit()
            
            InventoryHistoryService.record_history(
                db=db,
                sku=transfer.sku,
                warehouse=transfer.from_warehouse,
                old_stock=old_stock,
                new_stock=source_inventory.current_stock,
                reason="transfer_sent",
                reference=transfer.transfer_number,
                user_id=user_id,
            )
        
        transfer.actual_arrival = datetime.utcnow()
        updated = TransferWorkflowService._update_transfer_status(db, transfer, "received", user_id)
        
        import asyncio
        asyncio.create_task(
            TransferWorkflowService._send_notification(
                user_id=user_id,
                title=f"📦 Transfer Received: {transfer.transfer_number or transfer.id}",
                message=f"Transfer of {quantity} units of {transfer.sku} has been received at {transfer.to_warehouse}.",
                priority="success"
            )
        )
        
        return {"success": True, "transfer": updated}
    
    @staticmethod
    def complete_transfer(
        db: Session,
        transfer_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """Complete a received transfer."""
        transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
        if not transfer:
            return {"error": "Transfer not found"}
        
        if not TransferWorkflowService._validate_transition(transfer.status, "completed"):
            return {"error": f"Cannot complete transfer with status: {transfer.status}"}
        
        updated = TransferWorkflowService._update_transfer_status(db, transfer, "completed", user_id)
        
        import asyncio
        asyncio.create_task(
            TransferWorkflowService._send_notification(
                user_id=user_id,
                title=f"✅ Transfer Completed: {transfer.transfer_number or transfer.id}",
                message=f"Transfer of {transfer.transfer_quantity} units of {transfer.sku} has been completed.",
                priority="success"
            )
        )
        
        return {"success": True, "transfer": updated}
    
    @staticmethod
    def cancel_transfer(
        db: Session,
        transfer_id: int,
        user_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """Cancel a transfer."""
        transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
        if not transfer:
            return {"error": "Transfer not found"}
        
        if not TransferWorkflowService._validate_transition(transfer.status, "cancelled"):
            return {"error": f"Cannot cancel transfer with status: {transfer.status}"}
        
        updated = TransferWorkflowService._update_transfer_status(db, transfer, "cancelled", user_id)
        
        import asyncio
        asyncio.create_task(
            TransferWorkflowService._send_notification(
                user_id=user_id,
                title=f"⛔ Transfer Cancelled: {transfer.transfer_number or transfer.id}",
                message=f"Transfer of {transfer.transfer_quantity} units of {transfer.sku} was cancelled. Reason: {reason}",
                priority="warning"
            )
        )
        
        return {"success": True, "transfer": updated}