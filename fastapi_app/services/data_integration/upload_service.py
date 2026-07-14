# fastapi_app/services/data_integration/upload_service.py
import os
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime
import logging

from fastapi_app.models.upload_model import Upload
from fastapi_app.models.sync_log_model import SyncLog
from fastapi_app.models.raw_data_model import RawSales
from fastapi_app.models.data_source_model import DataSource
from fastapi_app.services.validation.validation_service import ValidationEngine
from fastapi_app.services.validation.validation_service import create_validation_error
from fastapi_app.utils.file_utils import save_uploaded_file, delete_file

logger = logging.getLogger(__name__)


def create_upload(
    db: Session,
    filename: str,
    file_bytes: bytes,
    uploaded_by: int | None = None,
    folder: str | None = None,
) -> Upload:
    """Save uploaded file and create database record."""
    
    file_info = save_uploaded_file(
        file_bytes=file_bytes,
        filename=filename,
        folder=folder,
    )

    upload = Upload(
        filename=file_info["original_filename"],
        unique_filename=file_info["filename"],
        file_path=file_info["file_path"],
        file_url=file_info["file_url"],
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
    if upload is None:
        return False

    if upload.file_path:
        delete_file(upload.file_path)

    db.delete(upload)
    db.commit()
    return True


def process_upload(db: Session, upload_id: int) -> Upload | None:
    """
    Process uploaded file with validation and raw data storage.
    Follows same flow as data source sync.
    """
    upload = get_upload(db, upload_id)
    if not upload:
        return None

    # Create sync log for upload - WITHOUT the new fields
    sync_log = SyncLog(
        datasource_id=None,  # Uploads don't have a data source
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(sync_log)
    db.commit()

    try:
        # Check file exists
        if not os.path.exists(upload.file_path):
            create_validation_error(
                db,
                source=f"upload:{upload.id}",
                error_type="missing_file",
                severity="high",
                rows_affected=0,
                status="failed",
                column_name="file",
                row_number=0,
                expected_value="file exists",
                actual_value="missing",
                error_message="Uploaded file not found on disk",
                suggestion="Check file permissions and storage"
            )
            upload.status = "failed"
            sync_log.status = "failed"
            sync_log.message = "File not found"
            sync_log.completed_at = datetime.utcnow()
            db.commit()
            return upload

        # Read the file
        try:
            # Support multiple file types
            if upload.filename.lower().endswith('.csv'):
                df = pd.read_csv(upload.file_path)
            elif upload.filename.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(upload.file_path)
            elif upload.filename.lower().endswith('.json'):
                df = pd.read_json(upload.file_path)
            else:
                raise ValueError(f"Unsupported file type: {upload.filename}")
                
        except Exception as exc:
            create_validation_error(
                db,
                source=f"upload:{upload.id}",
                error_type="read_error",
                severity="high",
                rows_affected=0,
                status="failed",
                column_name="file",
                row_number=0,
                expected_value="valid file format",
                actual_value=str(exc),
                error_message=f"Failed to read file: {str(exc)}",
                suggestion="Check file format and encoding"
            )
            upload.status = "failed"
            sync_log.status = "failed"
            sync_log.message = f"File read error: {str(exc)}"
            sync_log.completed_at = datetime.utcnow()
            db.commit()
            return upload

        sync_log.rows_processed = len(df)

        # STANDARDIZE FIRST
        df = ValidationEngine.standardize_dataframe(df, "sales")
        
        # VALIDATE SECOND
        is_valid, errors, stats = ValidationEngine.validate_dataframe(
            df, 
            source_type="sales",
            source_name=f"upload:{upload.id}",
            strict_mode=False
        )

        # Store validation errors with details
        for error in errors:
            create_validation_error(
                db,
                source=f"upload:{upload.id}",
                error_type=error.get('column_name', 'unknown'),
                severity=error.get('severity', 'medium'),
                rows_affected=stats.get('total_rows', 0),
                status="open",
                column_name=error.get('column_name'),
                row_number=error.get('row_number', 0),
                expected_value=error.get('expected_value', ''),
                actual_value=error.get('actual_value', ''),
                error_message=error.get('error_message', ''),
                suggestion=error.get('suggestion', '')
            )

        # Store raw data if valid enough
        if is_valid or stats['error_count'] < len(df) * 0.5:
            # Create a virtual data source for upload
            virtual_ds = DataSource(
                name=f"Upload_{upload.filename}",
                type="LOCAL_FOLDER",
                status="success",
                health="healthy",
                last_sync=datetime.utcnow()
            )
            db.add(virtual_ds)
            db.flush()  # Get the ID
            
            # Store raw data
            store_upload_raw_data(db, df, virtual_ds.id, sync_log.id)
            
            upload.status = "processed" if is_valid else "partial_success"
            sync_log.status = "success" if is_valid else "partial_success"
            sync_log.rows_validated = len(df) - stats['error_count']
        else:
            upload.status = "failed_validation"
            sync_log.status = "failed"
            sync_log.message = f"Validation failed with {stats['error_count']} errors"

        sync_log.rows_failed = stats['error_count']
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()

    except Exception as e:
        logger.error(f"Error processing upload {upload_id}: {str(e)}")
        upload.status = "failed"
        sync_log.status = "failed"
        sync_log.message = f"Processing error: {str(e)}"
        sync_log.error_details = str(e)
        sync_log.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(upload)
    return upload


def store_upload_raw_data(
    db: Session, 
    df: pd.DataFrame, 
    datasource_id: int, 
    sync_log_id: int
) -> None:
    """Store upload data in raw tables."""
    records = df.to_dict('records')
    
    field_mapping = {
        "date": "date",
        "demand": "demand",
        "revenue": "revenue",
        "units": "units",
        "sku": "sku"
    }
    
    for record in records:
        mapped_data = {}
        for source_field, target_field in field_mapping.items():
            if source_field in record:
                value = record[source_field]
                # Convert pandas Timestamp to datetime
                if hasattr(value, 'to_pydatetime'):
                    value = value.to_pydatetime()
                mapped_data[target_field] = value
        
        mapped_data['datasource_id'] = datasource_id
        mapped_data['sync_id'] = sync_log_id
        mapped_data['raw_data'] = record
        mapped_data['validation_status'] = "validated"
        
        try:
            obj = RawSales(**mapped_data)
            db.add(obj)
        except Exception as e:
            logger.error(f"Error storing raw data: {str(e)}")
            continue
    
    db.commit()