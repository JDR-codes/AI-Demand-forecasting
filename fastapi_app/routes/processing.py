#fastapi_app/routes/processing.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.processing_schema import (
    ProcessingJobCreate,
    ProcessingJobResponse,
    ProcessingStepResponse,
    ProcessingLogResponse
)
from fastapi_app.services.data_processing.processing_job_service import ProcessingJobService
from fastapi_app.services.data_processing.processing_log_service import ProcessingLogService
from fastapi_app.services.background.task_manager import TaskManager

router = APIRouter(prefix="/api/processing", tags=["Processing"])


@router.post("/start", response_model=ProcessingJobResponse)
def start_processing(
    config: ProcessingJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a new processing job."""
    job = ProcessingJobService.create_job(db, config, current_user.id)
    
    # Run in background
    TaskManager.run_processing_job(job.job_id)
    
    return job


@router.get("/jobs", response_model=List[ProcessingJobResponse])
def list_processing_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List processing jobs."""
    return ProcessingJobService.get_jobs(db, status, limit, offset)


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
def get_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific processing job."""
    job = ProcessingJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/steps", response_model=List[ProcessingStepResponse])
def get_processing_steps(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get steps for a processing job."""
    job = ProcessingJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.processing_steps


@router.get("/jobs/{job_id}/logs", response_model=List[ProcessingLogResponse])
def get_processing_logs(
    job_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get logs for a processing job."""
    job = ProcessingJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ProcessingLogService.get_logs(db, job.id, limit)


@router.post("/jobs/{job_id}/pause")
def pause_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a processing job."""
    if not ProcessingJobService.pause_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be paused")
    return {"message": "Job paused"}


@router.post("/jobs/{job_id}/resume")
def resume_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused processing job."""
    if not ProcessingJobService.resume_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be resumed")
    return {"message": "Job resumed"}


@router.post("/jobs/{job_id}/cancel")
def cancel_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a processing job."""
    if not ProcessingJobService.cancel_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return {"message": "Job cancelled"}


@router.post("/jobs/{job_id}/restart")
def restart_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restart a processing job."""
    job = ProcessingJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Create new job with same config
    config = ProcessingJobCreate(
        upload_id=job.upload_id,
        dataset_path=job.dataset_path
    )
    new_job = ProcessingJobService.create_job(db, config, current_user.id)
    TaskManager.run_processing_job(new_job.job_id)
    
    return {"message": "Job restarted", "new_job_id": new_job.job_id}


@router.post("/jobs/{job_id}/steps/{step_number}/retry")
def retry_processing_step(
    job_id: str,
    step_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a specific processing step."""
    if not ProcessingJobService.retry_step(db, job_id, step_number):
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Step retry initiated"}


@router.post("/jobs/{job_id}/steps/{step_number}/skip")
def skip_processing_step(
    job_id: str,
    step_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Skip a processing step."""
    if not ProcessingJobService.skip_step(db, job_id, step_number):
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Step skipped"}