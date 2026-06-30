from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from fastapi_app.models.data_source_model import DataSource


def get_all_data_sources(db: Session) -> List[DataSource]:
    return db.query(DataSource).all()


def create_data_source(db: Session, data: dict) -> DataSource:
    ds = DataSource(
        name=data["name"],
        type=data["type"],
        connection_string=data["connection_string"],
        status=data.get("status", "inactive"),
        health=data.get("health", "unknown"),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def get_data_source(db: Session, data_source_id: int) -> DataSource | None:
    return db.query(DataSource).filter(DataSource.id == data_source_id).first()


def update_data_source(db: Session, data_source_id: int, data: dict) -> DataSource | None:
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    for key, value in data.items():
        if value is not None and hasattr(ds, key):
            setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return ds


def delete_data_source(db: Session, data_source_id: int) -> bool:
    ds = get_data_source(db, data_source_id)
    if not ds:
        return False
    db.delete(ds)
    db.commit()
    return True


def sync_data_source(db: Session, data_source_id: int) -> DataSource | None:
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    ds.status = "syncing"
    ds.last_sync = datetime.utcnow()
    db.commit()
    db.refresh(ds)
    return ds


def schedule_sync_data_source(db: Session, data_source_id: int) -> DataSource | None:
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    ds.status = "scheduled"
    db.commit()
    db.refresh(ds)
    return ds


def get_data_source_health(db: Session, data_source_id: int) -> dict | None:
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    return {"health": ds.health, "status": ds.status, "last_sync": ds.last_sync}


def get_data_source_logs(db: Session, data_source_id: int) -> List[dict]:
    ds = get_data_source(db, data_source_id)
    if not ds:
        return []
    return [{"timestamp": datetime.utcnow(), "message": f"Log entry for data source {ds.id}"}]
