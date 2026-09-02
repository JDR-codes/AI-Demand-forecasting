#fastapi_app/routes/taining_jobs.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user, require_permission_dep
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import (
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingHistoryResponse,
    RetrainingScheduleResponse,
    OneShotScheduleRequest
)
from fastapi_app.schemas.training_config_schema import (
    TrainingConfigResponse,
    TrainingConfigUpdate,
    TrainingConfigCreate
)
from fastapi_app.services.forecast.training_service import TrainingService
from fastapi_app.services.forecast.model_registry_service import ModelRegistryService
from fastapi_app.services.forecast.training_config_service import TrainingConfigService

router = APIRouter(prefix="/api/training", tags=["Training"])


@router.post("/jobs", response_model=TrainingJobResponse)
def create_training_job(
    config: TrainingJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Create a new training job."""
    job = TrainingService.create_job(db, config, current_user.id)
    from fastapi_app.tasks.celery_tasks import run_training_job_task
    run_training_job_task.delay(job.job_id)
    return job


@router.get("/jobs", response_model=List[TrainingJobResponse])
def list_training_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
):
    """List training jobs."""
    return TrainingService.get_jobs(db, status, limit, offset)


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
def get_training_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
):
    """Get a specific training job."""
    job = TrainingService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel")
def cancel_training_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Cancel a training job."""
    if not TrainingService.cancel_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return {"message": "Job cancelled successfully"}


@router.get("/history", response_model=List[TrainingHistoryResponse])
def get_training_history(
    model_registry_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
):
    return ModelRegistryService.get_training_history(db, model_registry_id, limit)


# ============================================================================
# RETRAINING CONFIGURATIONS & SCHEDULES (Figma tab integration)
# ============================================================================

@router.get("/config", response_model=List[TrainingConfigResponse])
def list_training_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
):
    """List retraining configurations for all models."""
    return TrainingConfigService.get_configs(db)


@router.get("/config/{model_id}", response_model=TrainingConfigResponse)
def get_training_config(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
):
    """Get retraining configuration for a specific model registry ID."""
    model = ModelRegistryService.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model registry entry '{model_id}' not found")
        
    config = TrainingConfigService.get_config_by_model(db, model_id)
    if not config:
        config = TrainingConfigService.create_config(
            db,
            TrainingConfigCreate(model_registry_id=model_id)
        )
    return config


@router.put("/config/{model_id}", response_model=TrainingConfigResponse)
def update_training_config(
    model_id: str,
    update: TrainingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Update retraining configuration for a specific model."""
    model = ModelRegistryService.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model registry entry '{model_id}' not found")
        
    config = TrainingConfigService.get_config_by_model(db, model_id)
    if not config:
        config = TrainingConfigService.create_config(
            db,
            TrainingConfigCreate(model_registry_id=model_id)
        )
    return TrainingConfigService.update_config(db, config.id, update)


@router.get("/schedules", response_model=List[RetrainingScheduleResponse])
def list_upcoming_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
):
    """List upcoming scheduled retraining runs dynamically based on active frequencies."""
    from datetime import datetime, timedelta
    from fastapi_app.models.training_configuration_model import TrainingConfiguration
    
    # Get all enabled training configurations
    configs = db.query(TrainingConfiguration).filter(
        TrainingConfiguration.enabled == True,
        TrainingConfiguration.frequency != "manual"
    ).all()
    
    schedules = []
    now = datetime.utcnow()
    
    for config in configs:
        model = config.model_registry
        model_name = model.name if model else "Unknown"
        model_type = model.model_type if model else "unknown"
        
        # Calculate next run date based on frequency
        next_run = now
        if config.frequency == "daily":
            next_run = now + timedelta(days=1)
        elif config.frequency == "weekly":
            next_run = now + timedelta(weeks=1)
        elif config.frequency == "monthly":
            next_run = now + timedelta(days=30)
        else:
            continue
            
        schedules.append({
            "scheduled_run": next_run,
            "model_registry_id": config.model_registry_id or "unknown",
            "model_name": model_name,
            "model_type": model_type,
            "accuracy_threshold": config.accuracy_threshold,
            "status": "Scheduled"
        })
        
    schedules.sort(key=lambda x: x["scheduled_run"])
    return schedules


@router.post("/config/{model_id}/schedule-once")
def schedule_retraining_once(
    model_id: str,
    payload: OneShotScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Schedule model retraining to run only once at a specific date and time."""
    model = ModelRegistryService.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found in registry")
        
    from fastapi_app.services.scheduler.scheduler_service import scheduler
    
    # Schedule the one-shot job using DateTrigger
    scheduler.schedule_one_shot_retraining(model_id, payload.run_at)
    
    return {"message": f"One-shot retraining successfully scheduled for {payload.run_at}"}