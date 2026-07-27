# fastapi_app/routes/data_sources.py
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

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
    test_connection,
)
from fastapi_app.schemas.data_source_dashboard_schema import DataSourceDashboardMetrics
from fastapi_app.schemas.data_source_schema import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceOut,
)
from fastapi_app.services.scheduler.scheduler_service import scheduler
from fastapi_app.models.auth_model import User
from fastapi_app.services.data_integration.sync_job_service import SyncJobService
from fastapi_app.services.background.task_manager import TaskManager
from fastapi_app.models.sync_job_model import SyncJobStepDetail

router = APIRouter(prefix="/api/data-sources", tags=["Data Sources"])

# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard", response_model=DataSourceDashboardMetrics)
def get_data_source_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard metrics for data sources."""
    return get_data_source_dashboard_metrics(db)

# ============================================================================
# CRUD OPERATIONS
# ============================================================================

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

@router.get("/schedules")
def get_all_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all scheduled jobs."""
    return scheduler.get_scheduled_jobs()

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
    scheduler.remove_sync(data_source_id)
    return {"deleted": True}

# ============================================================================
# CONNECTION TEST
# ============================================================================

@router.post("/{data_source_id}/test")
def test_connection_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test connection to a data source."""
    result = test_connection(db, data_source_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Connection failed"))
    return result

@router.get("/{data_source_id}/test-history")
def get_connection_test_history(
    data_source_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get connection test history for a data source."""
    from fastapi_app.models.connection_history_model import ConnectionHistory
    from fastapi_app.services.data_integration.test_connection_service import TestConnectionService
    
    ds = get_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    history = db.query(ConnectionHistory).filter(
        ConnectionHistory.datasource_id == data_source_id
    ).order_by(ConnectionHistory.started_at.desc()).limit(limit).all()
    
    # If no test history exists yet, run an initial connection test to record history
    if not history:
        try:
            TestConnectionService.test_connection_with_history(db, ds)
            history = db.query(ConnectionHistory).filter(
                ConnectionHistory.datasource_id == data_source_id
            ).order_by(ConnectionHistory.started_at.desc()).limit(limit).all()
        except Exception as e:
            logger.warning(f"Auto connection test failed for data source {data_source_id}: {e}")
    
    return [
        {
            "id": h.id,
            "status": h.status,
            "response_time": h.response_time,
            "started_at": h.started_at,
            "completed_at": h.completed_at,
            "error_message": h.error_message
        }
        for h in history
    ]

# ============================================================================
# SYNC OPERATIONS
# ============================================================================

@router.post("/{data_source_id}/sync")
def sync_data_source_endpoint(
    data_source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync a data source."""
    ds = get_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Create sync job
    job = SyncJobService.create_job(db, data_source_id, triggered_by="manual")
    
    # Run in background
    TaskManager.run_sync_job(job.job_id)
    
    return {
        "message": "Sync job started",
        "job_id": job.job_id,
        "status": job.status.value
    }

@router.post("/sync-all")
def sync_all_data_sources_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync all data sources."""
    sources = get_all_data_sources(db)
    job_ids = []
    
    for ds in sources:
        job = SyncJobService.create_job(db, ds.id, triggered_by="manual")
        TaskManager.run_sync_job(job.job_id)
        job_ids.append(job.job_id)
    
    return {
        "message": f"Started sync for {len(job_ids)} data sources",
        "job_ids": job_ids
    }

@router.get("/sync-job/{job_id}")
def get_sync_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get sync job status."""
    job = SyncJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    
    return {
        "job_id": job.job_id,
        "datasource_id": job.datasource_id,
        "status": job.status.value,
        "current_step": job.current_step.value if job.current_step else None,
        "progress_percentage": job.progress_percentage,
        "rows_processed": job.rows_processed,
        "rows_total": job.rows_total,
        "rows_failed": job.rows_failed,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "duration_seconds": job.duration_seconds,
        "eta_seconds": job.eta_seconds,
        "triggered_by": job.triggered_by,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }

@router.get("/sync-job/{job_id}/steps")
def get_sync_job_steps(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get sync job steps."""
    job = SyncJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    
    steps = db.query(SyncJobStepDetail).filter(
        SyncJobStepDetail.sync_job_id == job.id
    ).order_by(SyncJobStepDetail.id).all()
    
    return [
        {
            "step_name": step.step_name.value if step.step_name else None,
            "status": step.status,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
            "duration_seconds": step.duration_seconds,
            "message": step.message
        }
        for step in steps
    ]

@router.delete("/sync-job/{job_id}")
def cancel_sync_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a sync job."""
    if not SyncJobService.cancel_job(db, job_id):
        raise HTTPException(status_code=404, detail="Sync job not found or already completed")
    return {"message": "Sync job cancelled", "job_id": job_id}

@router.post("/sync-job/{job_id}/retry")
def retry_sync_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed sync job."""
    job = SyncJobService.retry_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    return {
        "message": "Sync job retry started",
        "job_id": job.job_id
    }

# ============================================================================
# SCHEDULE OPERATIONS
# ============================================================================

@router.post("/{data_source_id}/schedule")
def schedule_sync_data_source_endpoint(
    data_source_id: int,
    frequency: str = Query(..., pattern="^(manual|hourly|daily|weekly|monthly|realtime)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Schedule a data source sync."""
    ds = schedule_sync_data_source(db, data_source_id, frequency)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {
        "message": f"Data source scheduled with frequency: {frequency}",
        "data_source": ds
    }

@router.put("/{data_source_id}/schedule")
def update_schedule_data_source_endpoint(
    data_source_id: int,
    frequency: str = Query(..., pattern="^(manual|hourly|daily|weekly|monthly|realtime)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a data source schedule."""
    ds = schedule_sync_data_source(db, data_source_id, frequency)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {
        "message": f"Data source schedule updated to: {frequency}",
        "data_source": ds
    }

@router.delete("/{data_source_id}/schedule")
def remove_schedule_data_source_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a data source schedule."""
    ds = get_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    ds.sync_frequency = "manual"
    db.commit()
    scheduler.remove_sync(data_source_id)
    
    return {"message": "Schedule removed", "data_source_id": data_source_id}



# ============================================================================
# HEALTH & LOGS
# ============================================================================

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
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_data_source_logs(db, data_source_id, limit)