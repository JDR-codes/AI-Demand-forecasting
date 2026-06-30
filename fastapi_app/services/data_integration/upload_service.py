import os
from typing import List
from sqlalchemy.orm import Session
import pandas as pd
from fastapi_app.models.upload_model import Upload
from fastapi_app.services.validation.validation_service import create_validation_error


def create_upload(db: Session, filename: str, file_path: str, uploaded_by: str | None = None) -> Upload:
    upload = Upload(
        filename=filename,
        file_path=file_path,
        status="uploaded",
        uploaded_by=uploaded_by,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def get_uploads(db: Session) -> List[Upload]:
    return db.query(Upload).all()


def get_upload(db: Session, upload_id: int) -> Upload | None:
    return db.query(Upload).filter(Upload.id == upload_id).first()


def delete_upload(db: Session, upload_id: int) -> bool:
    upload = get_upload(db, upload_id)
    if not upload:
        return False
    if os.path.exists(upload.file_path):
        os.remove(upload.file_path)
    db.delete(upload)
    db.commit()
    return True


def process_upload(db: Session, upload_id: int) -> Upload | None:
    upload = get_upload(db, upload_id)
    if not upload:
        return None

    if not os.path.exists(upload.file_path):
        create_validation_error(
            db,
            source=f"upload:{upload.id}",
            error_type="missing_file",
            severity="high",
            rows_affected=0,
            status="failed",
        )
        upload.status = "failed"
        db.commit()
        db.refresh(upload)
        return upload

    try:
        df = pd.read_csv(upload.file_path)
    except Exception as exc:
        create_validation_error(
            db,
            source=f"upload:{upload.id}",
            error_type="read_error",
            severity="high",
            rows_affected=0,
            status="failed",
        )
        upload.status = "failed"
        db.commit()
        db.refresh(upload)
        return upload

    required_columns = ["Date", "Demand"]
    errors_found = False

    for column in required_columns:
        if column not in df.columns:
            create_validation_error(
                db,
                source=f"upload:{upload.id}",
                error_type=f"missing_column:{column}",
                severity="high",
                rows_affected=0,
            )
            errors_found = True

    if "Demand" in df.columns:
        numeric_series = pd.to_numeric(df["Demand"], errors="coerce")
        if numeric_series.isna().any():
            create_validation_error(
                db,
                source=f"upload:{upload.id}",
                error_type="invalid_numeric_value",
                severity="medium",
                rows_affected=int(numeric_series.isna().sum()),
            )
            errors_found = True

    upload.status = "failed_validation" if errors_found else "processed"
    db.commit()
    db.refresh(upload)
    return upload
