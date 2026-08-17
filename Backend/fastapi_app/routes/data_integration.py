# fastapi_app/routes/data_integration.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from sqlalchemy.orm import Session
from fastapi_app.utils.file_utils import file_exists
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.upload_schema import UploadOut
from fastapi_app.services.data_integration.upload_service import create_upload
from fastapi_app.services.data_integration.upload_job_service import UploadJobService
from fastapi_app.services.background.task_manager import TaskManager
from typing import List
import os

router = APIRouter(prefix="/api/data-integration", tags=["Data Integration"])


@router.post("/upload-csv", response_model=UploadOut)
async def upload_csv(
    file: UploadFile = File(...),
    data_category: str = Form("sales", description="Data category for the upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    
    content = await file.read()
    
    upload = create_upload(
        db=db,
        filename=file.filename,
        file_bytes=content,
        uploaded_by=current_user.id,
        data_category=data_category,
        folder=None,
    )
    
    # Create upload job
    job = UploadJobService.create_job(db, upload.id)
    TaskManager.run_upload_job(job.job_id)
    
    return upload


@router.get("/validate")
def validate_csv(
    path: str,
    current_user: User = Depends(get_current_user),
):
    return {
        "valid": file_exists(path)
    }
