# fastapi_app/services/data_integration/sync_job_service.py
"""
Sync Job Service - Handles data source sync jobs with background execution.
"""
import uuid
import asyncio
import pandas as pd
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from fastapi_app.models.sync_job_model import SyncJob, SyncJobStatus, SyncJobStep, SyncJobStepDetail
from fastapi_app.models.data_source_model import DataSource
from fastapi_app.models.sync_log_model import SyncLog
from fastapi_app.services.data_integration.data_source_service import (
    fetch_data_from_source,
    store_raw_data_batch,
)
from fastapi_app.services.validation.validation_service import (
    ValidationEngine,
    create_validation_errors_batch
)
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.models.auth_model import User

logger = logging.getLogger(__name__)

SYNC_STEPS = [
    ("connecting", "Connecting to source"),
    ("downloading", "Downloading data"),
    ("validating", "Validating data"),
    ("saving", "Saving to database"),
]


class JobCancelledException(Exception):
    """Exception raised when a job is cancelled."""
    pass


class SyncJobService:
    """Service for managing sync jobs."""

    @staticmethod
    def create_job(
        db: Session,
        datasource_id: int,
        triggered_by: str = "manual"
    ) -> SyncJob:
        """Create a new sync job."""
        job_id = str(uuid.uuid4())

        job = SyncJob(
            job_id=job_id,
            datasource_id=datasource_id,
            status=SyncJobStatus.QUEUED,
            triggered_by=triggered_by,
            current_step=SyncJobStep.CONNECTING
        )

        db.add(job)
        db.flush()

        for i, (step_key, step_name) in enumerate(SYNC_STEPS):
            step = SyncJobStepDetail(
                sync_job_id=job.id,
                step_name=step_key,
                status="pending"
            )
            db.add(step)

        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[SyncJob]:
        """Get a sync job by ID."""
        return db.query(SyncJob).filter(SyncJob.job_id == job_id).first()

    @staticmethod
    def get_jobs(
        db: Session,
        datasource_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SyncJob]:
        """Get sync jobs with optional filtering."""
        query = db.query(SyncJob)
        if datasource_id:
            query = query.filter(SyncJob.datasource_id == datasource_id)
        if status:
            query = query.filter(SyncJob.status == status)
        return query.order_by(desc(SyncJob.created_at)).offset(offset).limit(limit).all()

    @staticmethod
    def _check_cancelled(db: Session, job_id: str):
        """Check if job has been cancelled."""
        db.expire_all()
        current_job = SyncJobService.get_job(db, job_id)
        if current_job and current_job.status == SyncJobStatus.CANCELLED:
            raise JobCancelledException("Job cancelled by user")

    @staticmethod
    def run_job(db: Session, job_id: str) -> Optional[SyncJob]:
        """Execute a sync job in background."""
        job = SyncJobService.get_job(db, job_id)
        if not job:
            return None

        if job.status != SyncJobStatus.QUEUED:
            return job

        ds = db.query(DataSource).filter(DataSource.id == job.datasource_id).first()
        if not ds:
            job.status = SyncJobStatus.FAILED
            job.error_message = "Data source not found"
            db.commit()
            return job

        # Set status to RUNNING and update datasource
        job.status = SyncJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        ds.status = "syncing"
        db.commit()

        try:
            # Step 1: Connecting
            SyncJobService._update_step(db, job.id, "connecting", "running")
            job.current_step = SyncJobStep.CONNECTING
            db.commit()

            SyncJobService._check_cancelled(db, job.job_id)

            manager.send_progress_update_sync(
                channel="sync",
                job_id=job.job_id,
                progress=25,
                step="Connecting to source",
                status="running"
            )

            SyncJobService._update_step(db, job.id, "connecting", "completed")
            SyncJobService._check_cancelled(db, job.job_id)

            # Step 2: Downloading
            SyncJobService._update_step(db, job.id, "downloading", "running")
            job.current_step = SyncJobStep.DOWNLOADING
            db.commit()

            data = fetch_data_from_source(ds)
            if not data:
                raise ValueError("No data retrieved from source")

            job.rows_total = len(data)
            db.commit()

            SyncJobService._update_step(db, job.id, "downloading", "completed")
            SyncJobService._check_cancelled(db, job.job_id)

            manager.send_progress_update_sync(
                channel="sync",
                job_id=job.job_id,
                progress=50,
                step="Downloading data",
                status="running"
            )

            # Step 3: Validating
            SyncJobService._update_step(db, job.id, "validating", "running")
            job.current_step = SyncJobStep.VALIDATING
            db.commit()

            df = pd.DataFrame(data)

            # Use data_category from DataSource
            source_type = ds.data_category or "sales"
            df = ValidationEngine.standardize_dataframe(df, source_type)
            is_valid, errors, stats = ValidationEngine.validate_dataframe(
                df,
                source_type,
                f"datasource:{ds.id}"
            )

            # Save validation errors
            if errors:
                create_validation_errors_batch(
                    db=db,
                    errors=errors,
                    datasource_id=ds.id,
                    source_prefix="datasource"
                )

            # Calculate affected rows
            affected_rows = sum(
                int(error.get("rows_affected", 0))
                for error in errors
            )

            affected_rows = min(
                affected_rows,
                len(df)
            )

            # Only high/critical problems block the sync
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

            job.rows_failed = affected_rows
            db.commit()

            SyncJobService._update_step(db, job.id, "validating", "completed")
            SyncJobService._check_cancelled(db, job.job_id)

            manager.send_progress_update_sync(
                channel="sync",
                job_id=job.job_id,
                progress=75,
                step="Validating data",
                status="running"
            )

            # Step 4: Saving
            SyncJobService._update_step(db, job.id, "saving", "running")
            job.current_step = SyncJobStep.SAVING
            db.commit()

            validation_status = "validated" if is_valid else "needs_review"

            can_store = (
                len(blocking_errors) == 0
                or blocking_rows < len(df) * 0.5
            )

            if can_store:
                store_raw_data_batch(
                    db,
                    df,
                    ds.id,
                    None,
                    source_type,
                    validation_status=validation_status
                )

                job.rows_processed = len(df)

                SyncJobService._update_step(
                    db,
                    job.id,
                    "saving",
                    "completed"
                )

                job.status = SyncJobStatus.COMPLETED

            else:
                job.rows_processed = 0

                SyncJobService._update_step(
                    db,
                    job.id,
                    "saving",
                    "failed"
                )

                job.status = SyncJobStatus.FAILED
                job.error_message = (
                    f"Validation failed: {affected_rows} of "
                    f"{len(df)} rows affected"
                )

            SyncJobService._check_cancelled(db, job.job_id)

            job.progress_percentage = 100.0
            job.completed_at = datetime.utcnow()
            job.duration_seconds = (
                job.completed_at - job.started_at
            ).total_seconds()

            db.commit()

            # Determine sync status for logs and datasource
            if job.status == SyncJobStatus.FAILED:
                sync_status = "failed"
            elif is_valid:
                sync_status = "success"
            else:
                sync_status = "partial_success"

            # Update data source
            ds.last_sync = datetime.utcnow()

            if sync_status == "success":
                ds.status = "success"
                ds.health = "healthy"
            elif sync_status == "partial_success":
                ds.status = "partial_success"
                ds.health = "degraded"
            else:
                ds.status = "failed"
                ds.health = "unhealthy"

            if can_store:
                ds.record_count = job.rows_processed or 0

            ds.health_score = max(
                0,
                100 - (
                    affected_rows / len(df) * 100
                    if len(df) > 0
                    else 0
                )
            )

            db.commit()

            # Send final WebSocket status
            if job.status == SyncJobStatus.COMPLETED:
                final_step = "Completed"
                final_status = "completed"
            else:
                final_step = "Validation Failed"
                final_status = "failed"

            manager.send_progress_update_sync(
                channel="sync",
                job_id=job.job_id,
                progress=100,
                step=final_step,
                status=final_status
            )

            # Create SyncLog record
            if sync_status != "failed":
                sync_message = (
                    f"Data source '{ds.name}' synced successfully. "
                    f"{job.rows_processed or 0} records processed."
                )
            else:
                sync_message = (
                    f"Data source '{ds.name}' sync failed validation. "
                    f"{affected_rows} of {len(df)} rows affected."
                )

            sync_log = SyncLog(
                datasource_id=ds.id,
                started_at=job.started_at,
                completed_at=job.completed_at,
                status=sync_status,
                rows_processed=job.rows_processed or 0,
                rows_failed=job.rows_failed or 0,
                duration_seconds=job.duration_seconds,
                message=sync_message,
                triggered_by=job.triggered_by
            )

            db.add(sync_log)
            db.commit()

            # Notification
            admin_users = db.query(User).filter(
                User.is_admin == True
            ).all()

            notification_success = (
                job.status == SyncJobStatus.COMPLETED
            )

            for admin in admin_users:
                NotificationService.create_sync_notification(
                    db=db,
                    user_id=admin.id,
                    datasource_name=ds.name,
                    success=notification_success,
                    message=sync_message
                )

        except JobCancelledException:
            job.status = SyncJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()

            if ds:
                ds.status = "idle"

            db.commit()

            manager.send_progress_update_sync(
                channel="sync",
                job_id=job.job_id,
                progress=100,
                step="Cancelled",
                status="cancelled"
            )

            logger.info(f"Sync job {job_id} cancelled by user")

        except Exception as e:
            logger.error(
                f"Sync job {job_id} failed: {str(e)}"
            )

            db.rollback()

            # Reload ORM objects after rollback
            job = SyncJobService.get_job(db, job_id)

            ds = None

            if job:
                ds = db.query(DataSource).filter(
                    DataSource.id == job.datasource_id
                ).first()

                job.status = SyncJobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()

                if job.started_at:
                    job.duration_seconds = (
                        job.completed_at - job.started_at
                    ).total_seconds()

            if ds:
                ds.status = "failed"
                ds.health = "unhealthy"

            db.commit()

            if job:
                manager.send_progress_update_sync(
                    channel="sync",
                    job_id=job.job_id,
                    progress=100,
                    step="Failed",
                    status="failed"
                )

            if ds and job:
                sync_log = SyncLog(
                    datasource_id=ds.id,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    status="failed",
                    rows_processed=job.rows_processed or 0,
                    rows_failed=job.rows_failed or 0,
                    duration_seconds=job.duration_seconds,
                    message=(
                        f"Data source '{ds.name}' "
                        f"sync failed: {str(e)}"
                    ),
                    error_details=str(e),
                    triggered_by=job.triggered_by
                )

                db.add(sync_log)
                db.commit()

                admin_users = db.query(User).filter(
                    User.is_admin == True
                ).all()

                for admin in admin_users:
                    NotificationService.create_sync_notification(
                        db=db,
                        user_id=admin.id,
                        datasource_name=ds.name,
                        success=False,
                        message=(
                            f"Data source '{ds.name}' "
                            f"sync failed: {str(e)}"
                        )
                    )

        db.refresh(job)
        return job

    @staticmethod
    def _update_step(db: Session, job_id: int, step_name: str, status: str):
        """Update a step's status."""
        step = db.query(SyncJobStepDetail).filter(
            SyncJobStepDetail.sync_job_id == job_id,
            SyncJobStepDetail.step_name == step_name
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
        """Cancel a sync job."""
        job = SyncJobService.get_job(db, job_id)
        if not job or job.status in [SyncJobStatus.COMPLETED, SyncJobStatus.FAILED]:
            return False

        job.status = SyncJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def retry_job(db: Session, job_id: str) -> Optional[SyncJob]:
        """Retry a failed sync job."""
        job = SyncJobService.get_job(db, job_id)
        if not job:
            return None

        new_job = SyncJobService.create_job(
            db=db,
            datasource_id=job.datasource_id,
            triggered_by="retry"
        )
        return SyncJobService.run_job(db, new_job.job_id)