from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi_app.services.data_integration.data_integration_service import save_uploaded_file, validate_csv_path
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.utils.file_utils import (
    save_uploaded_file,
    file_exists,
)
from fastapi_app.models.auth_model import User
from typing import List
import os

router = APIRouter(prefix="/api/data_integration")


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()

    file_info = save_uploaded_file(
        file_bytes=content,
        filename=file.filename,
    )

    return {
        "message": "uploaded",
        "file": file_info,
    }

def validate(
    path: str,
    current_user: User = Depends(get_current_user),
):
    return {
        "valid": file_exists(path)
    }
