from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.services.data_integration.upload_service import (
    create_upload,
    get_uploads,
    get_upload,
    delete_upload,
    process_upload,
)
from fastapi_app.schemas.upload_schema import UploadOut
from fastapi_app.models.auth_model import User
from fastapi_app.core.config import UPLOADS_DIR
import os

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])


@router.post("/file", response_model=UploadOut)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    dest = os.path.join(UPLOADS_DIR, file.filename)
    with open(dest, "wb") as f:
        f.write(content)
    upload = create_upload(db, file.filename, dest, uploaded_by=current_user.email)
    return upload


@router.get("/", response_model=list[UploadOut])
def list_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_uploads(db)


@router.get("/{upload_id}", response_model=UploadOut)
def get_upload_endpoint(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = get_upload(db, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


@router.delete("/{upload_id}")
def delete_upload_endpoint(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_upload(db, upload_id):
        raise HTTPException(status_code=404, detail="Upload not found")
    return {"deleted": True}


@router.post("/{upload_id}/process", response_model=UploadOut)
def process_upload_endpoint(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = process_upload(db, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload
