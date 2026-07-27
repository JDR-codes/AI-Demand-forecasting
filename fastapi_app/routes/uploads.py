# fastapi_app/routes/uploads.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Request
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from pathlib import Path
import os
import pandas as pd

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.upload_schema import UploadOut, UploadPreviewOut
from fastapi_app.services.data_integration.upload_service import (
    create_upload,
    get_uploads,
    get_upload,
    delete_upload,
    process_upload,
    get_upload_preview,
    get_upload_stats,
)
from fastapi_app.services.data_integration.upload_job_service import UploadJobService
from fastapi_app.services.background.task_manager import TaskManager

router = APIRouter(
    prefix="/api/uploads",
    tags=["Uploads"],
)

class FilePathsPayload(BaseModel):
    file_paths: List[str]

# ============================================================================
# UPLOAD OPERATIONS
# ============================================================================

@router.post("/", response_model=UploadOut)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a single file."""
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls", ".json")):
        raise HTTPException(
            status_code=400,
            detail="Only CSV, Excel, and JSON files are accepted",
        )

    file_bytes = await file.read()

    upload = create_upload(
        db=db,
        filename=file.filename,
        file_bytes=file_bytes,
        uploaded_by=current_user.id,
        folder=None,
    )

    # Create upload job
    job = UploadJobService.create_job(db, upload.id)
    TaskManager.run_upload_job(job.job_id)

    return UploadOut.model_validate(upload)


@router.post("/multiple", response_model=List[UploadOut])
async def upload_multiple_files(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload multiple files via multipart file binary uploads or file path strings."""
    content_type = request.headers.get("content-type", "")
    items_to_process = []
    
    if "application/json" in content_type:
        try:
            body_json = await request.json()
            if isinstance(body_json, dict) and "files" in body_json:
                raw_items = body_json["files"]
            elif isinstance(body_json, list):
                raw_items = body_json
            else:
                raw_items = [body_json]
            for item in raw_items:
                if isinstance(item, str):
                    items_to_process.append(item)
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            items_to_process = form.getlist("files")
        except Exception:
            pass
            
    if not items_to_process:
        raise HTTPException(
            status_code=400,
            detail="No files or file paths provided in request"
        )
        
    results = []
    processed_paths = set()
    
    for item in items_to_process:
        if isinstance(item, UploadFile):
            filename = item.filename
            if not filename.lower().endswith((".csv", ".xlsx", ".xls", ".json")):
                continue
            file_bytes = await item.read()
            upload = create_upload(
                db=db,
                filename=filename,
                file_bytes=file_bytes,
                uploaded_by=current_user.id,
                folder=None,
            )
            job = UploadJobService.create_job(db, upload.id)
            TaskManager.run_upload_job(job.job_id)
            results.append(upload)
        elif isinstance(item, str):
            cleaned_str = item.strip(' "[]\'')
            if not cleaned_str:
                continue
            parts = [p.strip(' "\'') for p in cleaned_str.replace('"', '').split(",") if p.strip(' "\'')]
            for path_str in parts:
                if path_str in processed_paths:
                    continue
                processed_paths.add(path_str)
                
                file_path = Path(path_str)
                if not file_path.exists() or not file_path.is_file():
                    raise HTTPException(status_code=400, detail=f"File not found on disk: {path_str}")
                
                filename = file_path.name
                if not filename.lower().endswith((".csv", ".xlsx", ".xls", ".json")):
                    continue
                
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                
                upload = create_upload(
                    db=db,
                    filename=filename,
                    file_bytes=file_bytes,
                    uploaded_by=current_user.id,
                    folder=None,
                )
                job = UploadJobService.create_job(db, upload.id)
                TaskManager.run_upload_job(job.job_id)
                results.append(upload)

    return [UploadOut.model_validate(u) for u in results]


@router.post("/from-paths", response_model=List[UploadOut])
def upload_from_file_paths(
    payload: FilePathsPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload multiple files directly from local file paths on disk."""
    results = []
    for path_str in payload.file_paths:
        file_path = Path(path_str)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"File not found on disk: {path_str}")
        
        filename = file_path.name
        if not filename.lower().endswith((".csv", ".xlsx", ".xls", ".json")):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        upload = create_upload(
            db=db,
            filename=filename,
            file_bytes=file_bytes,
            uploaded_by=current_user.id,
            folder=None,
        )
        
        job = UploadJobService.create_job(db, upload.id)
        TaskManager.run_upload_job(job.job_id)
        
        results.append(upload)
    
    return [UploadOut.model_validate(u) for u in results]


@router.get("/", response_model=List[UploadOut])
def list_uploads(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List uploads with optional filtering."""
    uploads = get_uploads(db, status, limit, offset)
    return [UploadOut.model_validate(u) for u in uploads]


@router.get("/stats")
def get_upload_stats_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload statistics."""
    return get_upload_stats(db)


# ============================================================================
# UPLOAD JOBS (Must be declared before /{upload_id} parameterized routes)
# ============================================================================

@router.get("/jobs")
def get_upload_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload jobs."""
    jobs = UploadJobService.get_jobs(db, status, limit, offset)
    return [
        {
            "job_id": j.job_id,
            "upload_id": j.upload_id,
            "status": j.status.value if j.status else None,
            "current_step": j.current_step.value if j.current_step else None,
            "progress_percentage": j.progress_percentage,
            "records_processed": j.records_processed,
            "records_total": j.records_total,
            "records_failed": j.records_failed,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "duration_seconds": j.duration_seconds,
            "error_message": j.error_message,
            "created_at": j.created_at,
            "updated_at": j.updated_at
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
def get_upload_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload job status."""
    job = UploadJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    
    return {
        "job_id": job.job_id,
        "upload_id": job.upload_id,
        "status": job.status.value if job.status else None,
        "current_step": job.current_step.value if job.current_step else None,
        "progress_percentage": job.progress_percentage,
        "records_processed": job.records_processed,
        "records_total": job.records_total,
        "records_failed": job.records_failed,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "duration_seconds": job.duration_seconds,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }


@router.get("/jobs/{job_id}/steps")
def get_upload_job_steps(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload job steps."""
    steps = UploadJobService.get_job_steps(db, job_id)
    if not steps:
        raise HTTPException(status_code=404, detail="Upload job not found")
    
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


@router.post("/jobs/{job_id}/cancel")
def cancel_upload_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an upload job."""
    if not UploadJobService.cancel_job(db, job_id):
        raise HTTPException(status_code=404, detail="Upload job not found or already completed")
    return {"message": "Upload job cancelled", "job_id": job_id}


@router.post("/jobs/{job_id}/retry")
def retry_upload_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed upload job."""
    job = UploadJobService.retry_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return {
        "message": "Upload job retry started",
        "job_id": job.job_id
    }


# ============================================================================
# PARAMETERIZED UPLOAD ROUTES
# ============================================================================

@router.get("/{upload_id}", response_model=UploadOut)
def get_upload_endpoint(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = get_upload(db, upload_id)
    if upload is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found",
        )
    return UploadOut.model_validate(upload)


@router.delete("/{upload_id}")
def delete_upload_endpoint(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_upload(db, upload_id):
        raise HTTPException(
            status_code=404,
            detail="Upload not found",
        )
    return {"deleted": True}


# ============================================================================
# PREVIEW & DOWNLOAD
# ============================================================================

@router.get("/{upload_id}/preview", response_model=UploadPreviewOut)
def preview_upload(
    upload_id: int,
    rows: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview upload data."""
    preview_data = get_upload_preview(db, upload_id, rows)
    if "error" in preview_data:
        raise HTTPException(
            status_code=404 if preview_data["error"] == "Upload not found" else 400,
            detail=preview_data["error"]
        )
    
    return UploadPreviewOut(
        columns=preview_data["columns"],
        rows=preview_data["rows"],
        row_count=preview_data["row_count"],
        upload_id=preview_data["upload_id"],
        filename=preview_data["filename"]
    )


@router.get("/{upload_id}/download")
def download_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download uploaded file."""
    from fastapi.responses import FileResponse
    
    upload = get_upload(db, upload_id)
    if upload is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found",
        )
    
    if not os.path.exists(upload.file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found on server",
        )
    
    return FileResponse(
        upload.file_path,
        filename=upload.filename,
        media_type="application/octet-stream"
    )


# ============================================================================
# PROCESSING
# ============================================================================

@router.post("/{upload_id}/process", response_model=UploadOut)
def process_upload_endpoint(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = process_upload(db, upload_id)
    if upload is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found",
        )
    return UploadOut.model_validate(upload)