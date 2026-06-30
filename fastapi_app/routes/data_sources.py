from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.services.data_integration.data_source_service import (
    get_all_data_sources,
    create_data_source,
    get_data_source,
    update_data_source,
    delete_data_source,
    sync_data_source,
    schedule_sync_data_source,
    get_data_source_health,
    get_data_source_logs,
)
from fastapi_app.schemas.data_source_schema import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceOut,
)
from fastapi_app.models.auth_model import User

router = APIRouter(prefix="/api/data-sources", tags=["Data Sources"])


@router.get("/", response_model=List[DataSourceOut])
def list_data_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_all_data_sources(db)


@router.post("/", response_model=DataSourceOut)
def create_data_source_endpoint(
    payload: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_data_source(db, payload.dict())


@router.get("/{data_source_id}", response_model=DataSourceOut)
def get_data_source_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


@router.put("/{data_source_id}", response_model=DataSourceOut)
def update_data_source_endpoint(
    data_source_id: int,
    payload: DataSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = update_data_source(db, data_source_id, payload.dict())
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


@router.delete("/{data_source_id}")
def delete_data_source_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_data_source(db, data_source_id):
        raise HTTPException(status_code=404, detail="Data source not found")
    return {"deleted": True}


@router.post("/{data_source_id}/sync", response_model=DataSourceOut)
def sync_data_source_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = sync_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


@router.post("/{data_source_id}/schedule-sync", response_model=DataSourceOut)
def schedule_sync_data_source_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = schedule_sync_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


@router.get("/{data_source_id}/health")
def data_source_health_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    health = get_data_source_health(db, data_source_id)
    if not health:
        raise HTTPException(status_code=404, detail="Data source not found")
    return health


@router.get("/{data_source_id}/logs")
def data_source_logs_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_data_source_logs(db, data_source_id)
