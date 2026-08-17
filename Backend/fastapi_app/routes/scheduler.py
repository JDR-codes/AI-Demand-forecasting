from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.services.scheduler.scheduler_service import scheduler

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])


@router.get("/jobs")
def get_scheduled_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all scheduled jobs with next run times."""
    jobs = scheduler.get_scheduled_jobs()
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/sync")
def get_scheduled_sync_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all scheduled sync jobs."""
    jobs = scheduler.get_sync_jobs()
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
def get_scheduled_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific scheduled job."""
    job = scheduler.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.post("/jobs/{job_id}/pause")
def pause_scheduled_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a scheduled job."""
    if not scheduler.pause_job(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"message": f"Job {job_id} paused", "job_id": job_id}


@router.post("/jobs/{job_id}/resume")
def resume_scheduled_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused scheduled job."""
    if not scheduler.resume_job(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"message": f"Job {job_id} resumed", "job_id": job_id}


@router.post("/jobs/{job_id}/run-now")
def run_scheduled_job_now(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a scheduled job immediately."""
    if not scheduler.run_now(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"message": f"Job {job_id} triggered to run now", "job_id": job_id}


@router.delete("/jobs/{job_id}")
def delete_scheduled_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a scheduled job."""
    if not scheduler.remove_job(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"message": f"Job {job_id} deleted", "job_id": job_id}


@router.get("/frequencies")
def get_valid_frequencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get valid frequency options."""
    from fastapi_app.services.scheduler.scheduler_service import VALID_FREQUENCIES
    return {"frequencies": VALID_FREQUENCIES}