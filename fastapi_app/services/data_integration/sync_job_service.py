#fastapi_app/data_integration/sync_job_service.py
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
from fastapi_app.services.data_integration.data_source_service import (
    fetch_data_from_source,
    store_raw_data_batch,
    get_source_type_name
)
from fastapi_app.services.validation.validation_service import ValidationEngine
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
        
        job.status = SyncJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # Step 1: Connecting
            SyncJobService._update_step(db, job.id, "connecting", "running")
            job.current_step = SyncJobStep.CONNECTING
            db.commit()
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="sync",
                    job_id=job.job_id,
                    progress=25,
                    step="Connecting to source",
                    status="running"
                )
            )
            
            # Step 2: Downloading
            SyncJobService._update_step(db, job.id, "downloading", "running")
            job.current_step = SyncJobStep.DOWNLOADING
            db.commit()
            
            data = fetch_data_from_source(ds)
            if not data:
                raise ValueError("No data retrieved from source")
            
            job.rows_total = len(data)
            db.commit()
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="sync",
                    job_id=job.job_id,
                    progress=50,
                    step="Downloading data",
                    status="running"
                )
            )
            
            # Step 3: Validating
            SyncJobService._update_step(db, job.id, "validating", "running")
            job.current_step = SyncJobStep.VALIDATING
            db.commit()
            
            df = pd.DataFrame(data)
            source_type = get_source_type_name(ds.provider)
            df = ValidationEngine.standardize_dataframe(df, source_type)
            is_valid, errors, stats = ValidationEngine.validate_dataframe(df, source_type, ds.name)
            
            job.rows_failed = len(errors)
            db.commit()
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="sync",
                    job_id=job.job_id,
                    progress=75,
                    step="Validating data",
                    status="running"
                )
            )
            
            # Step 4: Saving
            SyncJobService._update_step(db, job.id, "saving", "running")
            job.current_step = SyncJobStep.SAVING
            db.commit()
            
            if is_valid or len(errors) < len(df) * 0.5:
                store_raw_data_batch(db, df, ds.id, None, source_type)
                job.rows_processed = len(df) - len(errors)
            
            SyncJobService._update_step(db, job.id, "saving", "completed")
            
            job.status = SyncJobStatus.COMPLETED
            job.progress_percentage = 100.0
            job.completed_at = datetime.utcnow()
            job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            db.commit()
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="sync",
                    job_id=job.job_id,
                    progress=100,
                    step="Completed",
                    status="completed"
                )
            )
            
            # Update data source
            ds.last_sync = datetime.utcnow()
            ds.record_count = len(data)
            ds.health_score = 100 - (len(errors) / len(data) * 100 if data else 0)
            db.commit()
            
            # Notification
            admin_users = db.query(User).filter(User.is_admin == True).all()
            for admin in admin_users:
                NotificationService.create_sync_notification(
                    db=db,
                    user_id=admin.id,
                    datasource_name=ds.name,
                    success=True,
                    message=f"Data source '{ds.name}' synced successfully. {len(data)} records processed."
                )
            
        except Exception as e:
            logger.error(f"Sync job {job_id} failed: {str(e)}")
            job.status = SyncJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="sync",
                    job_id=job.job_id,
                    progress=100,
                    step="Failed",
                    status="failed"
                )
            )
            
            admin_users = db.query(User).filter(User.is_admin == True).all()
            for admin in admin_users:
                NotificationService.create_sync_notification(
                    db=db,
                    user_id=admin.id,
                    datasource_name=ds.name,
                    success=False,
                    message=f"Data source '{ds.name}' sync failed: {str(e)}"
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
        
        # Create new job with same datasource
        new_job = SyncJobService.create_job(
            db=db,
            datasource_id=job.datasource_id,
            triggered_by="retry"
        )
        return SyncJobService.run_job(db, new_job.job_id)