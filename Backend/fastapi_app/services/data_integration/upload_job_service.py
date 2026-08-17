# fastapi_app/services/data_integration/upload_job_service.py
"""
Upload Job Service - Handles upload processing with background execution.
"""
import uuid
import asyncio
import pandas as pd
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from fastapi_app.models.upload_job_model import (
    UploadJob,
    UploadJobStatus,
    UploadJobStep,
    UploadJobStepDetail
)
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.raw_data_model import RawSales, RawInventory, RawSupplier, RawProducts
from fastapi_app.services.validation.validation_service import (
    ValidationEngine,
    create_validation_errors_batch
)
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.models.auth_model import User

logger = logging.getLogger(__name__)

UPLOAD_STEPS = [
    ("upload", "Uploading file"),
    ("read", "Reading data"),
    ("validate", "Validating data"),
    ("store", "Storing data"),
]


class JobCancelledException(Exception):
    """Exception raised when a job is cancelled."""
    pass


# ============================================================================
# HELPER: Safe first non-None value (preserves 0)
# ============================================================================

def first_not_none(*values):
    """
    Return the first value that is not None.
    Unlike `or`, this preserves valid values such as 0.
    """
    for value in values:
        if value is not None:
            return value
    return None


def is_null_value(value):
    """
    Safely determine whether a scalar value is null.

    Avoids ambiguous truth-value errors for lists,
    dictionaries and arrays.
    """
    if value is None:
        return True

    # Containers are not treated as scalar null values
    if isinstance(value, (list, tuple, dict, set)):
        return False

    try:
        result = pd.isna(value)

        if isinstance(result, bool):
            return result

        # Handles numpy.bool_
        if hasattr(result, "item") and getattr(result, "ndim", 1) == 0:
            return bool(result.item())

        return False

    except (TypeError, ValueError):
        return False


class UploadJobService:
    """Service for managing upload jobs."""

    @staticmethod
    def create_job(
        db: Session,
        upload_id: int
    ) -> UploadJob:
        """Create a new upload job."""
        job_id = str(uuid.uuid4())

        job = UploadJob(
            job_id=job_id,
            upload_id=upload_id,
            status=UploadJobStatus.QUEUED,
            current_step=UploadJobStep.UPLOAD
        )

        db.add(job)
        db.flush()

        for i, (step_key, step_name) in enumerate(UPLOAD_STEPS):
            step = UploadJobStepDetail(
                upload_job_id=job.id,
                step_name=step_key,
                status="pending"
            )
            db.add(step)

        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[UploadJob]:
        """Get an upload job by ID."""
        return db.query(UploadJob).filter(UploadJob.job_id == job_id).first()

    @staticmethod
    def get_jobs(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[UploadJob]:
        """Get upload jobs with optional filtering."""
        query = db.query(UploadJob)
        if status:
            query = query.filter(UploadJob.status == status)
        return query.order_by(desc(UploadJob.created_at)).offset(offset).limit(limit).all()

    @staticmethod
    def get_job_steps(db: Session, job_id: str) -> List[UploadJobStepDetail]:
        """Get steps for a specific job."""
        job = UploadJobService.get_job(db, job_id)
        if not job:
            return []
        return db.query(UploadJobStepDetail).filter(
            UploadJobStepDetail.upload_job_id == job.id
        ).order_by(UploadJobStepDetail.id).all()

    @staticmethod
    def _check_cancelled(db: Session, job_id: str):
        """Check if job has been cancelled."""
        db.expire_all()
        current_job = UploadJobService.get_job(db, job_id)
        if current_job and current_job.status == UploadJobStatus.CANCELLED:
            raise JobCancelledException("Job cancelled by user")

    @staticmethod
    def run_job(db: Session, job_id: str) -> Optional[UploadJob]:
        """Execute an upload job in background."""
        job = UploadJobService.get_job(db, job_id)
        if not job:
            return None

        if job.status != UploadJobStatus.QUEUED:
            return job

        upload = db.query(Upload).filter(Upload.id == job.upload_id).first()
        if not upload:
            job.status = UploadJobStatus.FAILED
            job.error_message = "Upload not found"
            db.commit()
            return job

        job.status = UploadJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()

        try:
            # Step 1: Upload (already done)
            UploadJobService._update_step(db, job.id, "upload", "completed")
            job.current_step = UploadJobStep.READ
            upload.processing_progress = 20.0
            upload.processing_status = "reading"
            db.commit()

            UploadJobService._check_cancelled(db, job.job_id)

            manager.send_progress_update_sync(
                channel="upload",
                job_id=job.job_id,
                progress=20,
                step="Reading file",
                status="running"
            )

            # Step 2: Read
            UploadJobService._update_step(db, job.id, "read", "running")
            df = UploadJobService._read_file(upload.file_path)
            if df is None or len(df) == 0:
                raise ValueError("No data read from file")

            job.records_total = len(df)
            upload.rows = len(df)
            upload.columns = len(df.columns)
            upload.processing_progress = 50.0
            upload.processing_status = "validating"
            db.commit()

            UploadJobService._update_step(db, job.id, "read", "completed")
            UploadJobService._check_cancelled(db, job.job_id)

            manager.send_progress_update_sync(
                channel="upload",
                job_id=job.job_id,
                progress=50,
                step="Validating data",
                status="running"
            )

            # Step 3: Validate
            job.current_step = UploadJobStep.VALIDATE
            db.commit()
            UploadJobService._update_step(db, job.id, "validate", "running")

            source_type = upload.data_category
            valid_categories = {"sales", "inventory", "supplier", "products"}
            if not source_type or source_type not in valid_categories:
                raise ValueError(f"Invalid or missing data category: '{source_type}'")

            df = ValidationEngine.standardize_dataframe(df, source_type)
            is_valid, errors, stats = ValidationEngine.validate_dataframe(
                df,
                source_type,
                f"upload:{upload.id}"
            )

            if errors:
                create_validation_errors_batch(
                    db=db,
                    errors=errors,
                    upload_id=upload.id,
                    source_prefix="upload"
                )

            affected_rows = sum(
                int(error.get("rows_affected", 0))
                for error in errors
            )

            affected_rows = min(
                affected_rows,
                len(df)
            )

            # Only high/critical errors should block storage
            blocking_errors = [
                error
                for error in errors
                if error.get("severity") in ["critical", "high"]
            ]

            blocking_rows = sum(
                int(error.get("rows_affected", 0))
                for error in blocking_errors
            )

            blocking_rows = min(
                blocking_rows,
                len(df)
            )

            job.records_failed = affected_rows
            upload.processing_progress = 80.0
            upload.processing_status = "storing"
            db.commit()

            UploadJobService._update_step(db, job.id, "validate", "completed")
            UploadJobService._check_cancelled(db, job.job_id)

            manager.send_progress_update_sync(
                channel="upload",
                job_id=job.job_id,
                progress=80,
                step="Storing data",
                status="running"
            )

            # Step 4: Store
            job.current_step = UploadJobStep.STORE
            db.commit()
            UploadJobService._update_step(db, job.id, "store", "running")

            validation_status = "validated" if is_valid else "needs_review"

            can_store = (
                len(blocking_errors) == 0
                or blocking_rows < len(df) * 0.5
            )

            if can_store:
                UploadJobService._store_data(
                    db,
                    df,
                    upload.id,
                    job.id,
                    source_type,
                    validation_status
                )

                job.records_processed = len(df)
                job.status = UploadJobStatus.COMPLETED

                UploadJobService._update_step(
                    db,
                    job.id,
                    "store",
                    "completed"
                )

            else:
                job.records_processed = 0
                job.status = UploadJobStatus.FAILED
                job.error_message = (
                    f"Validation failed: {affected_rows} of "
                    f"{len(df)} rows affected"
                )

                UploadJobService._update_step(
                    db,
                    job.id,
                    "store",
                    "failed"
                )

            UploadJobService._check_cancelled(db, job.job_id)

            job.progress_percentage = 100.0
            job.completed_at = datetime.utcnow()
            job.duration_seconds = (
                job.completed_at - job.started_at
            ).total_seconds()
            db.commit()

            if job.status == UploadJobStatus.COMPLETED:
                upload.status = "processed"
                upload.processing_status = "completed"
            else:
                upload.status = "failed"
                upload.processing_status = "failed"

            upload.processed_at = datetime.utcnow()
            upload.processing_progress = 100.0
            upload.duration_seconds = job.duration_seconds

            db.commit()

            # Send final WebSocket status
            if job.status == UploadJobStatus.COMPLETED:
                final_step = "Completed"
                final_status = "completed"
            else:
                final_step = "Validation Failed"
                final_status = "failed"

            manager.send_progress_update_sync(
                channel="upload",
                job_id=job.job_id,
                progress=100,
                step=final_step,
                status=final_status
            )

            user = db.query(User).filter(
                User.id == upload.uploaded_by
            ).first()

            if user:
                upload_success = (
                    job.status == UploadJobStatus.COMPLETED
                )

                if upload_success:
                    upload_message = (
                        f"Upload '{upload.filename}' processed successfully. "
                        f"{job.records_processed or 0} records stored."
                    )
                else:
                    upload_message = (
                        f"Upload '{upload.filename}' failed validation. "
                        f"{job.records_failed or 0} of "
                        f"{job.records_total or 0} records affected."
                    )

                NotificationService.create_upload_notification(
                    db=db,
                    user_id=user.id,
                    filename=upload.filename,
                    success=upload_success,
                    rows=job.records_processed or 0,
                    message=upload_message
                )

        except JobCancelledException:
            job.status = UploadJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            db.commit()

            upload.processing_status = "cancelled"
            upload.status = "pending"
            db.commit()

            manager.send_progress_update_sync(
                channel="upload",
                job_id=job.job_id,
                progress=100,
                step="Cancelled",
                status="cancelled"
            )

            logger.info(f"Upload job {job_id} cancelled by user")

        except Exception as e:
            logger.error(
                f"Upload job {job_id} failed: {str(e)}"
            )

            db.rollback()

            # Reload after rollback
            job = UploadJobService.get_job(db, job_id)

            upload = db.query(Upload).filter(
                Upload.id == job.upload_id
            ).first() if job else None

            if job:
                job.status = UploadJobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()

                if job.started_at:
                    job.duration_seconds = (
                        job.completed_at - job.started_at
                    ).total_seconds()

            if upload:
                upload.processing_status = "failed"
                upload.status = "failed"

            db.commit()

            if job:
                manager.send_progress_update_sync(
                    channel="upload",
                    job_id=job.job_id,
                    progress=100,
                    step="Failed",
                    status="failed"
                )

            if upload and upload.uploaded_by:
                user = db.query(User).filter(
                    User.id == upload.uploaded_by
                ).first()

                if user:
                    NotificationService.create_upload_notification(
                        db=db,
                        user_id=user.id,
                        filename=upload.filename,
                        success=False,
                        rows=0,
                        message=(
                            f"Upload '{upload.filename}' "
                            f"failed: {str(e)}"
                        )
                    )

        db.refresh(job)
        return job

    @staticmethod
    def _read_file(file_path: str) -> Optional[pd.DataFrame]:
        """Read file based on extension."""
        try:
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                return pd.read_excel(file_path)
            elif file_path.endswith('.json'):
                return pd.read_json(file_path)
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
        return None

    @staticmethod
    def _store_data(
        db: Session,
        df: pd.DataFrame,
        upload_id: int,
        job_id: int,
        data_category: str,
        validation_status: str = "validated"
    ):
        """Store data in appropriate raw table based on data_category."""
        records = df.to_dict('records')
        objects_to_add = []

        model_map = {
            "sales": RawSales,
            "inventory": RawInventory,
            "supplier": RawSupplier,
            "products": RawProducts
        }

        if data_category not in model_map:
            raise ValueError(f"Unsupported data category: '{data_category}'")

        model_class = model_map[data_category]

        field_mapping = {
            "sales": {
                "date": "date",
                "demand": "demand",
                "revenue": "revenue",
                "units": "units",
                "sku": "sku"
            },
            "inventory": {
                "warehouse": "warehouse",
                "stock": "stock",
                "reorder_level": "reorder_level",
                "last_updated": "last_updated",
                "sku": "sku"
            },
            "supplier": {
                "supplier": "supplier",
                "lead_time": "lead_time",
                "price": "price",
                "min_order": "min_order",
                "sku": "sku"
            },
            "products": {
                "name": "name",
                "category": "category",
                "price": "price",
                "sku": "sku"
            }
        }

        mapping = field_mapping.get(data_category, {})

        for record in records:
            mapped_data = {}
            for source_field, target_field in mapping.items():
                if source_field in record:
                    mapped_data[target_field] = record[source_field]

            # Safe fallbacks using first_not_none (preserves 0)
            if mapped_data.get("sku") is None:
                mapped_data["sku"] = first_not_none(
                    record.get("sku"),
                    record.get("product_id"),
                    record.get("product"),
                )

            if data_category == "sales":
                if mapped_data.get("date") is None:
                    mapped_data["date"] = first_not_none(
                        record.get("date"),
                        record.get("timestamp"),
                    )

                if mapped_data.get("demand") is None:
                    mapped_data["demand"] = first_not_none(
                        record.get("demand"),
                        record.get("demand_qty"),
                        record.get("units_sold"),
                    )

                if mapped_data.get("revenue") is None:
                    mapped_data["revenue"] = first_not_none(
                        record.get("revenue"),
                        record.get("revenue_amount"),
                        record.get("sales"),
                    )

                if mapped_data.get("units") is None:
                    mapped_data["units"] = first_not_none(
                        record.get("units"),
                        record.get("units_sold"),
                        record.get("quantity"),
                    )

            # Convert to appropriate Python types to prevent DB errors
            if "date" in mapped_data and mapped_data["date"] is not None:
                try:
                    mapped_data["date"] = pd.to_datetime(mapped_data["date"]).to_pydatetime()
                except Exception:
                    pass

            if "last_updated" in mapped_data and mapped_data["last_updated"] is not None:
                try:
                    mapped_data["last_updated"] = pd.to_datetime(mapped_data["last_updated"]).to_pydatetime()
                except Exception:
                    pass

            # Safe numeric conversion for integer/float columns
            for col in ["stock", "reorder_level", "lead_time", "min_order", "units"]:
                if col in mapped_data and mapped_data[col] is not None:
                    try:
                        mapped_data[col] = int(float(mapped_data[col]))
                    except (ValueError, TypeError):
                        pass

            for col in ["price", "demand", "revenue"]:
                if col in mapped_data and mapped_data[col] is not None:
                    try:
                        mapped_data[col] = float(mapped_data[col])
                    except (ValueError, TypeError):
                        pass

            for key, value in list(mapped_data.items()):
                if is_null_value(value):
                    mapped_data[key] = None

            mapped_data["upload_id"] = upload_id
            mapped_data["validation_status"] = validation_status

            raw_record = {}
            for key, value in record.items():
                if is_null_value(value):
                    raw_record[key] = None
                elif hasattr(value, 'to_pydatetime'):
                    raw_record[key] = value.isoformat()
                elif hasattr(value, 'tolist'):
                    raw_record[key] = value.tolist()
                elif hasattr(value, 'item'):
                    raw_record[key] = value.item()
                elif isinstance(value, (datetime, pd.Timestamp)):
                    raw_record[key] = value.isoformat()
                else:
                    raw_record[key] = value

            mapped_data['raw_data'] = raw_record

            try:
                obj = model_class(**mapped_data)
                objects_to_add.append(obj)
            except Exception as e:
                logger.error(f"Error storing record: {str(e)}")
                continue

        if objects_to_add:
            db.add_all(objects_to_add)
            db.commit()
            logger.info(f"Stored {len(objects_to_add)} records in {data_category} table")

    @staticmethod
    def _update_step(db: Session, job_id: int, step_name: str, status: str):
        """Update a step's status."""
        step = db.query(UploadJobStepDetail).filter(
            UploadJobStepDetail.upload_job_id == job_id,
            UploadJobStepDetail.step_name == step_name
        ).first()

        if step:
            step.status = status
            if status == "running":
                step.started_at = datetime.utcnow()
            elif status in ["completed", "failed"]:
                step.completed_at = datetime.utcnow()
                if step.started_at:
                    step.duration_seconds = (step.completed_at - step.started_at).total_seconds()
            db.commit()

    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        """Cancel an upload job."""
        job = UploadJobService.get_job(db, job_id)
        if not job or job.status in [UploadJobStatus.COMPLETED, UploadJobStatus.FAILED]:
            return False

        job.status = UploadJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def retry_job(db: Session, job_id: str) -> Optional[UploadJob]:
        """Retry a failed upload job."""
        job = UploadJobService.get_job(db, job_id)
        if not job:
            return None

        new_job = UploadJobService.create_job(db, job.upload_id)
        return UploadJobService.run_job(db, new_job.job_id)