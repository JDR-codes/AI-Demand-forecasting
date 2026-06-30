from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi_app.services.data_integration.data_integration_service import save_uploaded_file, validate_csv_path
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.core.config import UPLOADS_DIR
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
    dest = os.path.join(UPLOADS_DIR, file.filename)
    path = save_uploaded_file(content, dest)
    return {"message": "uploaded", "path": path}


@router.get("/validate")
def validate(path: str, current_user: User = Depends(get_current_user)):
    ok = validate_csv_path(path)
    return {"valid": ok}
