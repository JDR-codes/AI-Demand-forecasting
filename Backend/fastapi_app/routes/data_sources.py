# fastapi_app/routes/data_sources.py
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    get_data_source_dashboard_metrics,
    get_data_source_logs,
)
from fastapi_app.schemas.data_source_dashboard_schema import DataSourceDashboardMetrics
from fastapi_app.schemas.data_source_schema import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceOut,
    DataSourceLookup,
    SyncScheduleCreate,
    SyncScheduleUpdate,
    SyncScheduleOut,
)
from fastapi_app.services.scheduler.scheduler_service import scheduler
from fastapi_app.models.auth_model import User
from fastapi_app.services.data_integration.sync_job_service import SyncJobService
from fastapi_app.services.background.task_manager import TaskManager
from fastapi_app.services.data_integration.test_connection_service import TestConnectionService
from fastapi_app.models.data_source_model import DataSource
from fastapi_app.models.sync_schedule_model import SyncSchedule

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
# SCHEDULE OPERATIONS - NEW
# ============================================================================

@router.post("/schedules", response_model=SyncScheduleOut)
def create_schedule_endpoint(
    payload: SyncScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new sync schedule."""
    # Validate timezone
    try:
        ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timezone: {payload.timezone}"
        )

    # Validate data sources for specific scope
    if payload.scope == "specific":
        if not payload.data_source_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one data source is required for 'specific' scope"
            )

        sources = (
            db.query(DataSource)
            .filter(
                DataSource.id.in_(payload.data_source_ids),
                DataSource.is_enabled.is_(True)
            )
            .all()
        )

        if len(sources) != len(set(payload.data_source_ids)):
            raise HTTPException(
                status_code=400,
                detail="One or more selected data sources are unavailable or disabled"
            )

    # Create schedule in database
    schedule = SyncSchedule(
        scope=payload.scope,
        schedule_type=payload.schedule_type,
        frequency=payload.frequency,
        run_method=payload.run_method,
        timezone=payload.timezone,
        data_source_ids=payload.data_source_ids,
        custom_runs=[r.model_dump(mode="json") for r in payload.custom_runs] if payload.custom_runs else None,
        run_times=[r.isoformat() for r in payload.run_times] if payload.run_times else None,
        weekdays=payload.weekdays,
        interval_value=payload.interval_value,
        interval_unit=payload.interval_unit,
        window_start_time=payload.window_start_time,
        window_end_time=payload.window_end_time,
        start_date=payload.start_date,
        end_date=payload.end_date,
        monthly_runs=[r.model_dump(mode="json") for r in payload.monthly_runs] if payload.monthly_runs else None,
        is_active=True,
        created_by=current_user.id
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Register with APScheduler
    try:
        scheduler.schedule_sync_from_db(db, schedule.id)
    except Exception as e:
        # If scheduling fails, deactivate the schedule
        schedule.is_active = False
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule: {str(e)}"
        )

    return schedule


@router.get("/schedules", response_model=List[SyncScheduleOut])
def list_schedules_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sync schedules."""
    schedules = db.query(SyncSchedule).order_by(SyncSchedule.created_at.desc()).all()
    return schedules


@router.get("/schedules/{schedule_id}", response_model=SyncScheduleOut)
def get_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific sync schedule."""
    schedule = db.query(SyncSchedule).filter(SyncSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.put("/schedules/{schedule_id}", response_model=SyncScheduleOut)
def update_schedule_endpoint(
    schedule_id: int,
    payload: SyncScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a sync schedule."""
    schedule = db.query(SyncSchedule).filter(SyncSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Validate timezone
    try:
        ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timezone: {payload.timezone}"
        )

    # Validate data sources for specific scope
    if payload.scope == "specific":
        if not payload.data_source_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one data source is required for 'specific' scope"
            )

        unique_ids = list(set(payload.data_source_ids))
        sources = (
            db.query(DataSource)
            .filter(
                DataSource.id.in_(unique_ids),
                DataSource.is_enabled.is_(True)
            )
            .all()
        )

        if len(sources) != len(unique_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more selected data sources are unavailable or disabled"
            )

    # Update schedule
    schedule.scope = payload.scope
    schedule.schedule_type = payload.schedule_type
    schedule.frequency = payload.frequency
    schedule.run_method = payload.run_method
    schedule.timezone = payload.timezone
    schedule.data_source_ids = payload.data_source_ids
    schedule.custom_runs = [r.model_dump(mode="json") for r in payload.custom_runs] if payload.custom_runs else None
    schedule.run_times = [r.isoformat() for r in payload.run_times] if payload.run_times else None
    schedule.weekdays = payload.weekdays
    schedule.interval_value = payload.interval_value
    schedule.interval_unit = payload.interval_unit
    schedule.window_start_time = payload.window_start_time
    schedule.window_end_time = payload.window_end_time
    schedule.start_date = payload.start_date
    schedule.end_date = payload.end_date
    schedule.monthly_runs = [r.model_dump(mode="json") for r in payload.monthly_runs] if payload.monthly_runs else None
    schedule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(schedule)

    # Re-register with APScheduler
    scheduler.remove_schedule_jobs(schedule_id)
    if schedule.is_active:
        try:
            scheduler.schedule_sync_from_db(db, schedule.id)
        except Exception as e:
            schedule.is_active = False
            db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reschedule: {str(e)}"
            )

    return schedule


@router.delete("/schedules/{schedule_id}")
def delete_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a sync schedule."""
    schedule = db.query(SyncSchedule).filter(SyncSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Remove from APScheduler
    scheduler.remove_schedule_jobs(schedule_id)

    db.delete(schedule)
    db.commit()

    return {"deleted": True, "schedule_id": schedule_id}


@router.post("/schedules/{schedule_id}/toggle")
def toggle_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle a schedule's active status."""
    schedule = db.query(SyncSchedule).filter(SyncSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_active = not schedule.is_active
    schedule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(schedule)

    if schedule.is_active:
        scheduler.schedule_sync_from_db(db, schedule.id)
        message = "Schedule activated"
    else:
        scheduler.remove_schedule_jobs(schedule_id)
        message = "Schedule deactivated"

    return {"message": message, "is_active": schedule.is_active}


# ============================================================================
# CRUD OPERATIONS
# ============================================================================


@router.get("/", response_model=List[DataSourceOut])
def list_data_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_all_data_sources(db)


@router.get("/lookup", response_model=List[DataSourceLookup])
def lookup_data_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve lightweight public metadata for data source picker dropdowns."""
    return get_all_data_sources(db)


@router.post("/", response_model=DataSourceOut)
def create_data_source_endpoint(
    payload: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.dict()
    data["created_by"] = current_user.id
    return create_data_source(db, data)


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
    ds = get_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")

    # Clean up schedules referencing this data source
    schedules = db.query(SyncSchedule).filter(SyncSchedule.scope == "specific").all()
    for schedule in schedules:
        ids = schedule.data_source_ids or []
        if data_source_id in ids or str(data_source_id) in ids:
            # Remove the ID
            new_ids = [x for x in ids if x != data_source_id and str(x) != str(data_source_id)]
            
            # Remove existing scheduler jobs first
            scheduler.remove_schedule_jobs(schedule.id)
            
            if not new_ids:
                # Deactivate the schedule if no sources remain
                schedule.is_active = False
                schedule.data_source_ids = []
                db.commit()
            else:
                # Update data source IDs and reschedule
                schedule.data_source_ids = new_ids
                db.commit()
                if schedule.is_active:
                    scheduler.schedule_sync_from_db(db, schedule.id)

    if not delete_data_source(db, data_source_id):
        raise HTTPException(status_code=404, detail="Data source not found")
        
    scheduler.remove_sync(data_source_id)
    return {"deleted": True}


# ============================================================================
# TEST CONNECTION
# ============================================================================

@router.post("/{data_source_id}/test-connection")
def test_connection_endpoint(
    data_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test connection for a data source."""
    ds = get_data_source(db, data_source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")

    result = TestConnectionService.test_connection_with_history(db, ds)

    if result.get("success"):
        ds.status = "active"
        ds.health = "healthy"
    else:
        ds.status = "error"
        ds.health = "error"
        ds.last_error = result.get("message")

    db.commit()

    return result


# ============================================================================
# SYNC OPERATIONS
# ============================================================================

@router.post("/{data_source_id}/sync")
def sync_data_source_endpoint(
    data_source_id: int,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync all enabled data sources."""
    sources = (
        db.query(DataSource)
        .filter(DataSource.is_enabled.is_(True))
        .all()
    )

    if not sources:
        return {
            "message": "No enabled data sources found",
            "sources": 0,
            "job_ids": []
        }

    job_ids = []

    for ds in sources:
        job = SyncJobService.create_job(db, ds.id, triggered_by="manual")
        TaskManager.run_sync_job(job.job_id)
        job_ids.append(job.job_id)

    return {
        "message": f"Started sync for {len(sources)} data sources",
        "sources": len(sources),
        "job_ids": job_ids
    }







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
    """Get logs for a data source."""
    logs = get_data_source_logs(db, data_source_id, limit)
    return {"logs": logs, "count": len(logs)}