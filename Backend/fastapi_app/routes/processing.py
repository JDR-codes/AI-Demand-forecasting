#fastapi_app/routes/processing.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional

from fastapi_app.core.dependencies import get_current_user, require_permission_dep
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.processing_job_model import (
    ProcessingJob,
    ProcessingJobStepDetail,
    ProcessingOutlierResult,
    ProcessingJobStatus,
)
from fastapi_app.schemas.processing_schema import (
    ProcessingJobCreate,
    ProcessingJobResponse,
    ProcessingStepResponse,
)
from fastapi_app.services.data_processing.processing_job_service import ProcessingJobService
from fastapi_app.services.background.task_manager import TaskManager

router = APIRouter(prefix="/api/processing", tags=["Processing"])


def _format_duration_seconds(seconds: Optional[float]) -> str:
    """Convert a float duration into a HH:MM:SS string for the UI."""
    if seconds is None:
        return "00:00:00"

    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds_part = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds_part:02d}"


@router.get("/dashboard")
def get_processing_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:read"))
):
    """Return a UI-ready dashboard summary for the data-processing screen."""
    latest_job = db.query(ProcessingJob).order_by(desc(ProcessingJob.created_at)).first()
    if not latest_job:
        return {
            "title": "Data Processing",
            "subtitle": "Data cleaning, transformation, feature engineering pipeline",
            "summary": {
                "steps_complete": 0,
                "total_steps": 7,
                "records_processed": 0,
                "outliers_detected": 0,
                "pipeline_duration": "00:00:00",
                "status": "idle"
            },
            "steps": [],
            "tabs": ["Pipeline", "Outliers", "Feature Engineering", "Logs"]
        }

    steps = db.query(ProcessingJobStepDetail).filter(
        ProcessingJobStepDetail.processing_job_id == latest_job.id
    ).order_by(ProcessingJobStepDetail.step_number).all()

    completed_steps = [step for step in steps if step.status == "completed"]
    running_step = next((step for step in steps if step.status == "running"), None)
    outlier_total = db.query(func.coalesce(func.sum(ProcessingOutlierResult.total_outliers), 0)).filter(
        ProcessingOutlierResult.processing_job_id == latest_job.id
    ).scalar() or 0

    duration_seconds = latest_job.duration_seconds
    if duration_seconds is None and latest_job.started_at and latest_job.completed_at:
        duration_seconds = (latest_job.completed_at - latest_job.started_at).total_seconds()

    dashboard_steps = []
    for step in steps:
        dashboard_steps.append({
            "step_number": step.step_number,
            "name": step.step_name.value if hasattr(step.step_name, 'value') else str(step.step_name),
            "status": step.status,
            "progress": step.progress,
            "records_processed": step.records_processed,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            "duration": _format_duration_seconds(step.duration_seconds),
            "message": step.message
        })

    return {
        "title": "Data Processing",
        "subtitle": "Data cleaning, transformation, feature engineering pipeline",
        "job_id": latest_job.job_id,
        "summary": {
            "steps_complete": len(completed_steps),
            "total_steps": len(steps),
            "records_processed": latest_job.records_processed or latest_job.records_loaded or 0,
            "outliers_detected": int(outlier_total),
            "pipeline_duration": _format_duration_seconds(duration_seconds),
            "status": latest_job.status.value if hasattr(latest_job.status, 'value') else str(latest_job.status),
            "current_step": running_step.step_name.value if running_step and hasattr(running_step.step_name, 'value') else str(running_step.step_name) if running_step else None,
            "progress_percentage": latest_job.progress_percentage,
            "message": latest_job.error_message
        },
        "steps": dashboard_steps,
        "tabs": ["Pipeline", "Outliers", "Feature Engineering", "Logs"],
        "actions": {
            "pause_enabled": latest_job.status == ProcessingJobStatus.RUNNING,
            "rerun_enabled": True
        }
    }


@router.post("/", response_model=ProcessingJobResponse)
def start_processing(
    config: Optional[ProcessingJobCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:run"))
):
    """Start a new processing job."""
    if config is None or (not config.data_source_ids and not config.upload_ids):
        # Default to loading ALL data sources and uploads owned by this user
        from fastapi_app.models.data_source_model import DataSource
        from fastapi_app.models.upload_model import Upload
        
        all_ds_ids = [ds.id for ds in db.query(DataSource).filter(DataSource.created_by == current_user.id).all()]
        all_upload_ids = [u.id for u in db.query(Upload).filter(Upload.uploaded_by == current_user.id).all()]
        
        config = ProcessingJobCreate(
            data_source_ids=all_ds_ids,
            upload_ids=all_upload_ids,
            category_mode="all",
            categories=[],
            merge_strategy="separate",
            deduplicate=True,
            run_validation=True,
            run_outlier_detection=True,
            run_feature_engineering=True
        )
        
    try:
        job = ProcessingJobService.create_job(db, config, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Run in background
    TaskManager.run_processing_job(job.job_id)
    
    return job



@router.get("/available-inputs")
def get_available_inputs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:read"))
):
    """Get selectable data sources and uploads for data processing."""
    from fastapi_app.models.data_source_model import DataSource
    from fastapi_app.models.upload_model import Upload
    
    sources = db.query(DataSource).filter(DataSource.created_by == current_user.id).all()
    uploads = db.query(Upload).filter(Upload.uploaded_by == current_user.id).all()

    
    return {
        "data_sources": [
            {
                "id": s.id,
                "name": s.name,
                "category": s.data_category,
                "type": s.type.value if hasattr(s.type, "value") else str(s.type),
                "status": s.status
            }
            for s in sources
        ],
        "uploads": [
            {
                "id": u.id,
                "filename": u.filename,
                "category": u.data_category,
                "status": u.status if hasattr(u, "status") else "processed"
            }
            for u in uploads
        ],
        "categories": ["sales", "inventory", "supplier", "products"]
    }


@router.get("/jobs", response_model=List[ProcessingJobResponse])
def list_processing_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:read"))
):
    """List all processing jobs created by the current user."""
    jobs = db.query(ProcessingJob).filter(
        ProcessingJob.created_by == current_user.id
    ).order_by(desc(ProcessingJob.created_at)).offset(offset).limit(limit).all()
    return jobs


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
def get_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:read"))
):
    """Get a specific processing job."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/inputs")
def get_job_inputs(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:read"))
):
    """Get all inputs for a specific processing job."""
    from fastapi_app.models.processing_job_input_model import ProcessingJobInput
    
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    inputs = db.query(ProcessingJobInput).filter(
        ProcessingJobInput.processing_job_id == job.id
    ).all()
    
    return {
        "job_id": job.job_id,
        "total_inputs": len(inputs),
        "inputs": [
            {
                "id": x.id,
                "input_type": x.input_type,
                "data_source_id": x.data_source_id,
                "upload_id": x.upload_id,
                "category": x.category,
                "status": x.status,
                "records_loaded": x.records_loaded,
                "records_processed": x.records_processed,
                "error_message": x.error_message,
                "started_at": x.started_at.isoformat() if x.started_at else None,
                "completed_at": x.completed_at.isoformat() if x.completed_at else None
            }
            for x in inputs
        ]
    }


@router.get("/jobs/{job_id}/categories")
def get_processing_categories(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:read"))
):
    """Get category summary for a specific processing job."""
    from fastapi_app.models.processing_job_input_model import ProcessingJobInput
    
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    inputs = db.query(ProcessingJobInput).filter(
        ProcessingJobInput.processing_job_id == job.id
    ).all()
    
    summary = {}
    for item in inputs:
        category = item.category
        if category not in summary:
            summary[category] = {
                "inputs": 0,
                "completed": 0,
                "failed": 0,
                "records_loaded": 0,
                "records_processed": 0
            }
        data = summary[category]
        data["inputs"] += 1
        if item.status == "completed":
            data["completed"] += 1
        elif item.status == "failed":
            data["failed"] += 1
        data["records_loaded"] += (item.records_loaded or 0)
        data["records_processed"] += (item.records_processed or 0)
        
    return {
        "job_id": job_id,
        "categories": summary
    }


@router.get("/jobs/{job_id}/steps", response_model=List[ProcessingStepResponse])
def get_processing_steps(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:read"))
):
    """Get steps for a processing job."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.processing_steps


@router.post("/jobs/{job_id}/pause")
def pause_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:run"))
):
    """Pause a processing job."""
    # Ensure job ownership
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not ProcessingJobService.pause_job(db, job_id):
        raise HTTPException(status_code=400, detail="Cannot pause job")
    return {"message": "Job paused"}


@router.post("/jobs/{job_id}/resume")
def resume_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:run"))
):
    """Resume a paused processing job."""
    # Ensure job ownership
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not ProcessingJobService.resume_job(db, job_id):
        raise HTTPException(status_code=400, detail="Cannot resume job")
    return {"message": "Job resumed"}


@router.post("/jobs/{job_id}/cancel")
def cancel_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:run"))
):
    """Cancel a processing job."""
    # Ensure job ownership
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not ProcessingJobService.cancel_job(db, job_id):
        raise HTTPException(status_code=400, detail="Cannot cancel job")
    return {"message": "Job cancelled"}


@router.post("/jobs/{job_id}/restart")
def restart_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("processing:run"))
):
    """Restart a processing job deterministically."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Reconstruct original configuration selections
    from fastapi_app.models.processing_job_input_model import ProcessingJobInput
    
    inputs = db.query(ProcessingJobInput).filter(
        ProcessingJobInput.processing_job_id == job.id
    ).all()
    
    ds_ids = [x.data_source_id for x in inputs if x.input_type == "data_source"]
    upload_ids = [x.upload_id for x in inputs if x.input_type == "upload"]
    
    config = ProcessingJobCreate(
        data_source_ids=ds_ids,
        upload_ids=upload_ids,
        category_mode=job.category_mode,
        categories=job.categories or [],
        merge_strategy=job.merge_strategy,
        deduplicate=job.deduplicate,
        run_validation=job.run_validation,
        run_outlier_detection=job.run_outlier_detection,
        run_feature_engineering=job.run_feature_engineering
    )
    new_job = ProcessingJobService.create_job(db, config, current_user.id)
    TaskManager.run_processing_job(new_job.job_id)
    
    return {"message": "Job restarted", "new_job_id": new_job.job_id}

