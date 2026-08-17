# fastapi_app/routes/uploads.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query, Request
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.upload_schema import UploadOut, UploadPreviewOut
from fastapi_app.schemas.data_source_schema import DataCategory
from fastapi_app.services.data_integration.upload_service import (
    create_upload,
    get_uploads,
    get_upload,
    delete_upload,
    get_upload_preview,
    get_upload_stats,
)
from fastapi_app.services.data_integration.upload_job_service import UploadJobService
from fastapi_app.services.background.task_manager import TaskManager

router = APIRouter(
    prefix="/api/uploads",
    tags=["Uploads"],
)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


# ============================================================================
# HELPERS
# ============================================================================

def validate_upload_file(filename: str, file_bytes: bytes) -> None:
    """Validate uploaded file."""
    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Maximum file size is 100 MB (got {len(file_bytes) / (1024 * 1024):.1f} MB)"
        )

    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only CSV, Excel, and JSON files are accepted (got {ext})"
        )


def validate_filename(filename: str) -> bool:
    """Check if filename has allowed extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# ============================================================================
# UPLOAD OPERATIONS
# ============================================================================

@router.post("/", response_model=UploadOut)
async def upload_file(
    file: UploadFile = File(...),
    data_category: str = Form("sales", description="Data category for the upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a single file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    valid_categories = {"sales", "inventory", "supplier", "products"}
    if data_category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data category: '{data_category}'. Allowed values are: {', '.join(valid_categories)}"
        )

    file_bytes = await file.read()

    # Validate file
    validate_upload_file(file.filename, file_bytes)

    upload = create_upload(
        db=db,
        filename=file.filename,
        file_bytes=file_bytes,
        uploaded_by=current_user.id,
        data_category=data_category,
        folder=None,
    )

    # Create upload job
    job = UploadJobService.create_job(db, upload.id)
    TaskManager.run_upload_job(job.job_id)

    return UploadOut.model_validate(upload)


@router.post("/multiple", response_model=List[UploadOut])
async def upload_multiple_files(
    request: Request,
    files: Optional[List[str]] = Form(None),
    file_paths: Optional[str] = Form(None),
    data_category: str = Form("sales", description="Data category for uploads"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload multiple files via multipart file binary uploads or file path strings."""
    logger.info(f"Multiple uploads endpoint hit. files={files}, file_paths={file_paths}")
    
    valid_categories = {"sales", "inventory", "supplier", "products"}
    if data_category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data category: '{data_category}'. Allowed values are: {', '.join(valid_categories)}"
        )

    items_to_process = []

    if files:
        items_to_process.extend(files)

    if file_paths:
        parts = [p.strip(' "\'[]') for p in file_paths.replace('"', '').split(",") if p.strip(' "\'[]')]
        items_to_process.extend(parts)

    if not items_to_process:
        content_type = request.headers.get("content-type", "")
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
                form_files = form.getlist("files")
                if form_files:
                    items_to_process.extend(form_files)
                form_paths = form.getlist("file_paths")
                if form_paths:
                    items_to_process.extend(form_paths)
            except Exception:
                pass

    # Filter out Swagger UI placeholder values
    items_to_process = [item for item in items_to_process if not (isinstance(item, str) and item.strip() == "string")]

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
            if not filename or not validate_filename(filename):
                continue
            file_bytes = await item.read()
            try:
                validate_upload_file(filename, file_bytes)
            except HTTPException as e:
                logger.warning(f"Skipping file {filename}: {e.detail}")
                continue
            upload = create_upload(
                db=db,
                filename=filename,
                file_bytes=file_bytes,
                uploaded_by=current_user.id,
                data_category=data_category,
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
                if not filename or not validate_filename(filename):
                    continue

                with open(file_path, "rb") as f:
                    file_bytes = f.read()

                try:
                    validate_upload_file(filename, file_bytes)
                except HTTPException as e:
                    logger.warning(f"Skipping file {filename}: {e.detail}")
                    continue

                upload = create_upload(
                    db=db,
                    filename=filename,
                    file_bytes=file_bytes,
                    uploaded_by=current_user.id,
                    data_category=data_category,
                    folder=None,
                )
                job = UploadJobService.create_job(db, upload.id)
                TaskManager.run_upload_job(job.job_id)
                results.append(upload)

    if not results:
        raise HTTPException(
            status_code=400,
            detail="No valid files were uploaded"
        )

    return [UploadOut.model_validate(u) for u in results]


@router.get("/", response_model=List[UploadOut])
def list_uploads(
    status: Optional[str] = None,
    data_category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List uploads with optional filtering."""
    uploads = get_uploads(db, status, data_category, limit, offset)
    return [UploadOut.model_validate(u) for u in uploads]


@router.get("/stats")
def get_upload_stats_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload statistics."""
    return get_upload_stats(db)


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