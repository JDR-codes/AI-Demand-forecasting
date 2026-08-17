#fastapi_app/routes/taining_jobs.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import (
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingHistoryResponse
)
from fastapi_app.services.forecast.training_service import TrainingService
from fastapi_app.services.forecast.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/api/training", tags=["Training"])


@router.post("/jobs", response_model=TrainingJobResponse)
def create_training_job(
    config: TrainingJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    """List training jobs."""
    return TrainingService.get_jobs(db, status, limit, offset)


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
def get_training_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    return ModelRegistryService.get_training_history(db, model_registry_id, limit)