# fastapi_app/services/data_integration/upload_service.py
"""
Upload Service - Handles upload CRUD operations and file management.
"""
import os
import uuid
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from fastapi_app.models.upload_model import Upload
from fastapi_app.utils.file_utils import save_uploaded_file, delete_file
from fastapi_app.core.config import MEDIA_DIR

logger = logging.getLogger(__name__)


def create_upload(
    db: Session,
    filename: str,
    file_bytes: bytes,
    uploaded_by: int,
    folder: Optional[str] = None
) -> Upload:
    """
    Create a new upload record and save the file.
    """
    # Save file to disk
    file_info = save_uploaded_file(
        file_bytes=file_bytes,
        filename=filename,
        folder=folder or "uploads"
    )
    
    # Generate checksum
    checksum = hashlib.md5(file_bytes).hexdigest()
    
    # Create upload record
    upload = Upload(
        filename=filename,
        unique_filename=file_info["unique_filename"],
        file_path=file_info["file_path"],
        file_url=file_info["file_url"],
        file_size=file_info["file_size"],
        mime_type=file_info["mime_type"],
        checksum=checksum,
        extension=file_info["extension"],
        status="pending",
        uploaded_by=uploaded_by,
        uploaded_at=datetime.utcnow()
    )
    
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    logger.info(f"Upload created: {upload.id} - {filename}")
    return upload


def get_upload(db: Session, upload_id: int) -> Optional[Upload]:
    """Get a single upload by ID."""
    return db.query(Upload).filter(Upload.id == upload_id).first()


def get_uploads(
    db: Session,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Upload]:
    """Get uploads with optional filtering."""
    query = db.query(Upload)
    if status:
        query = query.filter(Upload.status == status)
    return query.order_by(desc(Upload.uploaded_at)).offset(offset).limit(limit).all()


def delete_upload(db: Session, upload_id: int) -> bool:
    """
    Delete an upload and its associated file.
    """
    upload = get_upload(db, upload_id)
    if not upload:
        return False
    
    # Delete file from disk
    if upload.file_path and os.path.exists(upload.file_path):
        delete_file(upload.file_path)
    
    db.delete(upload)
    db.commit()
    
    logger.info(f"Upload deleted: {upload_id}")
    return True


def process_upload(db: Session, upload_id: int) -> Optional[Upload]:
    """
    Process an upload (run validation and store data).
    This is a synchronous wrapper for the background job.
    """
    upload = get_upload(db, upload_id)
    if not upload:
        return None
    
    if upload.status == "processed":
        return upload
    
    # Update status
    upload.status = "processing"
    upload.processing_status = "processing"
    db.commit()
    
    try:
        # Import here to avoid circular imports
        from fastapi_app.services.data_integration.upload_job_service import UploadJobService
        
        # Create and run job
        job = UploadJobService.create_job(db, upload_id)
        UploadJobService.run_job(db, job.job_id)
        
        db.refresh(upload)
        return upload
        
    except Exception as e:
        logger.error(f"Failed to process upload {upload_id}: {str(e)}")
        upload.status = "failed"
        upload.processing_status = "failed"
        db.commit()
        return upload


def get_upload_preview(db: Session, upload_id: int, rows: int = 20) -> Dict[str, Any]:
    """
    Get a preview of the uploaded file.
    """
    import pandas as pd
    
    upload = get_upload(db, upload_id)
    if not upload:
        return {"error": "Upload not found"}
    
    if not os.path.exists(upload.file_path):
        return {"error": "File not found on server"}
    
    try:
        if upload.filename.lower().endswith('.csv'):
            df = pd.read_csv(upload.file_path, nrows=rows)
        elif upload.filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(upload.file_path, nrows=rows)
        elif upload.filename.lower().endswith('.json'):
            df = pd.read_json(upload.file_path)
        else:
            return {"error": "Unsupported file format for preview"}
        
        return {
            "columns": df.columns.tolist(),
            "rows": df.head(rows).to_dict('records'),
            "row_count": len(df),
            "upload_id": upload_id,
            "filename": upload.filename
        }
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}


def get_upload_stats(db: Session) -> Dict[str, Any]:
    """
    Get statistics about uploads.
    """
    from sqlalchemy import func
    
    total = db.query(func.count(Upload.id)).scalar() or 0
    pending = db.query(func.count(Upload.id)).filter(Upload.status == "pending").scalar() or 0
    processed = db.query(func.count(Upload.id)).filter(Upload.status == "processed").scalar() or 0
    failed = db.query(func.count(Upload.id)).filter(Upload.status == "failed").scalar() or 0
    
    total_size = db.query(func.sum(Upload.file_size)).scalar() or 0
    
    return {
        "total": total,
        "pending": pending,
        "processed": processed,
        "failed": failed,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0
    }