# fastapi_app/routes/forecast_jobs.py
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import (
    ForecastJobCreate,
    ForecastJobResponse,
    ForecastJobStepResponse,
    ForecastResultResponse,
    ForecastChartData,
    ForecastSummary
)
from fastapi_app.services.forecast.forecast_job_service import ForecastJobService
from fastapi_app.services.forecast.forecast_execution_service import ForecastExecutionService
from fastapi_app.services.forecast.forecast_chart_service import ForecastChartService
from fastapi_app.services.background.task_manager import TaskManager

router = APIRouter(prefix="/api/forecast/jobs", tags=["Forecast Jobs"])


# ============================================================================
# JOB CRUD
# ============================================================================

@router.post("/", response_model=ForecastJobResponse)
def create_forecast_job(
    config: ForecastJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new forecast job."""
    job = ForecastJobService.create_job(db, config, current_user.id)
    return job


@router.get("/", response_model=List[ForecastJobResponse])
def list_forecast_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List forecast jobs with optional filtering."""
    return ForecastJobService.get_jobs(db, status, limit, offset)


@router.get("/{job_id}", response_model=ForecastJobResponse)
def get_forecast_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific forecast job with steps and results."""
    job = ForecastJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}")
def delete_forecast_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a forecast job (only if not running)."""
    job = ForecastJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in ["running", "queued"]:
        raise HTTPException(status_code=400, detail="Cannot delete a running job. Cancel it first.")
    
    db.delete(job)
    db.commit()
    return {"message": "Job deleted successfully"}


# ============================================================================
# JOB STEPS
# ============================================================================

@router.get("/{job_id}/steps", response_model=List[ForecastJobStepResponse])
def get_forecast_job_steps(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get steps for a forecast job."""
    job = ForecastJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.job_steps


# ============================================================================
# JOB EXECUTION (Start/Pause/Resume/Cancel/Retry)
# ============================================================================

@router.post("/{job_id}/start", response_model=ForecastJobResponse)
def start_forecast_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a forecast job."""
    job = ForecastJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "queued":
        raise HTTPException(status_code=400, detail=f"Job is already {job.status}")
    
    # Start in background
    TaskManager.run_forecast_job(job_id)
    
    db.refresh(job)
    return job


@router.post("/{job_id}/pause")
def pause_forecast_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a running forecast job."""
    if not ForecastExecutionService.pause_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be paused")
    return {"message": "Job paused"}


@router.post("/{job_id}/resume")
def resume_forecast_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused forecast job."""
    if not ForecastExecutionService.resume_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be resumed")
    return {"message": "Job resumed"}


@router.post("/{job_id}/cancel")
def cancel_forecast_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a forecast job."""
    if not ForecastExecutionService.cancel_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return {"message": "Job cancelled successfully"}


@router.post("/{job_id}/retry")
def retry_forecast_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a failed forecast job."""
    job = ForecastExecutionService.retry_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job retry started", "new_job_id": job.job_id}


# ============================================================================
# JOB STATUS (Live)
# ============================================================================

@router.get("/{job_id}/status")
def get_forecast_live_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get live status for UI."""
    status = ForecastExecutionService.get_live_status(db, job_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


# ============================================================================
# JOB RESULTS
# ============================================================================

@router.get("/{job_id}/results", response_model=ForecastChartData)
def get_forecast_results(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get forecast results with historical/forecast separation."""
    chart_data = ForecastChartService.get_chart_data(db, job_id)
    if "error" in chart_data:
        raise HTTPException(status_code=404, detail=chart_data["error"])
    return chart_data


@router.get("/{job_id}/summary", response_model=ForecastSummary)
def get_forecast_summary(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary statistics."""
    summary = ForecastChartService.get_summary(db, job_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    return summary


@router.get("/{job_id}/chart")
def get_forecast_chart(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chart data for the forecast."""
    data = ForecastChartService.get_chart_data(db, job_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/{job_id}/peaks")
def get_forecast_peaks(
    job_id: str,
    top_n: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get peak demand days."""
    peaks = ForecastChartService.get_peaks(db, job_id, top_n)
    if "error" in peaks:
        raise HTTPException(status_code=404, detail=peaks["error"])
    return peaks