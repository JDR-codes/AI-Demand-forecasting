from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from fastapi_app.models.alert_model import Alert, AlertSeverity, AlertCategory
from fastapi_app.schemas.alert_schema import AlertCreate
from fastapi_app.models.inventory_model import InventorySKU, WarehouseInventory


class AlertService:

    @staticmethod
    def get_alerts(
        db: Session,
        severity: Optional[AlertSeverity] = None,
        category: Optional[AlertCategory] = None,
        is_read: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        query = db.query(Alert)

        if severity is not None:
            query = query.filter(Alert.severity == severity)
        if category is not None:
            query = query.filter(Alert.category == category)
        if is_read is not None:
            query = query.filter(Alert.is_read == is_read)

        query = query.order_by(Alert.created_at.desc())

        total = query.count()
        unread = db.query(Alert).filter(Alert.is_read == False).count()
        items = query.offset(skip).limit(limit).all()

        return {"total": total, "unread": unread, "items": items}

    @staticmethod
    def create_alert(db: Session, payload: AlertCreate) -> Alert:
        # Validate SKU if provided
        if payload.sku:
            sku_obj = db.query(InventorySKU).filter(InventorySKU.sku == payload.sku).first()
            if not sku_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid SKU '{payload.sku}'. SKU not found in inventory.",
                )

        # Validate warehouse if provided
        if payload.warehouse:
            if payload.sku:
                wh = (
                    db.query(WarehouseInventory)
                    .filter(
                        WarehouseInventory.sku == payload.sku,
                        WarehouseInventory.warehouse == payload.warehouse,
                    )
                    .first()
                )
                if not wh:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Invalid warehouse '{payload.warehouse}' for SKU '{payload.sku}'. "
                            "Please provide a valid warehouse for the given SKU."
                        ),
                    )
            else:
                wh_any = (
                    db.query(WarehouseInventory)
                    .filter(WarehouseInventory.warehouse == payload.warehouse)
                    .first()
                )
                if not wh_any:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid warehouse '{payload.warehouse}'. Warehouse not found in records.",
                    )

        # Validate region if provided — ensure it exists for the provided sku/warehouse combination
        if payload.region:
            region_ok = None
            if payload.sku and payload.warehouse:
                region_ok = (
                    db.query(WarehouseInventory)
                    .filter(
                        WarehouseInventory.sku == payload.sku,
                        WarehouseInventory.warehouse == payload.warehouse,
                        WarehouseInventory.region == payload.region,
                    )
                    .first()
                )
                if not region_ok:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Invalid region '{payload.region}' for SKU '{payload.sku}' and warehouse '{payload.warehouse}'. "
                            "Please provide a region that exists for the given SKU and warehouse."
                        ),
                    )
            elif payload.warehouse:
                region_ok = (
                    db.query(WarehouseInventory)
                    .filter(
                        WarehouseInventory.warehouse == payload.warehouse,
                        WarehouseInventory.region == payload.region,
                    )
                    .first()
                )
                if not region_ok:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Invalid region '{payload.region}' for warehouse '{payload.warehouse}'. "
                            "Region not found for this warehouse."
                        ),
                    )
            elif payload.sku:
                region_ok = (
                    db.query(WarehouseInventory)
                    .filter(
                        WarehouseInventory.sku == payload.sku,
                        WarehouseInventory.region == payload.region,
                    )
                    .first()
                )
                if not region_ok:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Invalid region '{payload.region}' for SKU '{payload.sku}'. "
                            "Region not found for this SKU."
                        ),
                    )
            else:
                region_any = (
                    db.query(WarehouseInventory)
                    .filter(WarehouseInventory.region == payload.region)
                    .first()
                )
                if not region_any:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid region '{payload.region}'. Region not found in records.",
                    )

        alert = Alert(
            title=payload.title,
            message=payload.message,
            severity=payload.severity,
            category=payload.category,
            sku=payload.sku,
            warehouse=payload.warehouse,
            region=payload.region,
            is_read=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def mark_as_read(db: Session, alert_id: int) -> Dict[str, Any]:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert with id={alert_id} not found",
            )

        if alert.is_read:
            return {"id": alert.id, "is_read": True, "message": "Alert was already marked as read"}

        alert.is_read = True
        alert.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)

        return {"id": alert.id, "is_read": alert.is_read, "message": "Alert marked as read successfully"}

    @staticmethod
    def delete_alert(db: Session, alert_id: int) -> Dict[str, Any]:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert with id={alert_id} not found",
            )

        db.delete(alert)
        db.commit()

        return {"id": alert_id, "message": f"Alert {alert_id} deleted successfully"}