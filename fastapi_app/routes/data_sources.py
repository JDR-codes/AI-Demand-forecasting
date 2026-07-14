# fastapi_app/routes/data_sources.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
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
    get_data_source_dashboard_metrics,
)
from fastapi_app.schemas.data_source_dashboard_schema import DataSourceDashboardMetrics
from fastapi_app.schemas.data_source_schema import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceOut,
)
from fastapi_app.services.scheduler.scheduler_service import scheduler
from fastapi_app.models.auth_model import User

router = APIRouter(prefix="/api/data-sources", tags=["Data Sources"])


# ============================================================================
# SPECIFIC ROUTES FIRST (BEFORE PARAMETERIZED ROUTES)
# ============================================================================

@router.get("/dashboard", response_model=DataSourceDashboardMetrics)
def get_data_source_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard metrics for data sources."""
    return get_data_source_dashboard_metrics(db)


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


# ============================================================================
# PARAMETERIZED ROUTES (WITH {data_source_id})
# ============================================================================

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
    # Also remove from scheduler
    scheduler.remove_sync(data_source_id)
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
    frequency: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    ds = schedule_sync_data_source(db, data_source_id, frequency)
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