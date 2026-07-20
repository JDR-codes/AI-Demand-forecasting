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
from fastapi_app.models.raw_data_model import RawSales
from fastapi_app.services.validation.validation_service import ValidationEngine
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
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="upload",
                    job_id=job.job_id,
                    progress=20,
                    step="Reading file",
                    status="running"
                )
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
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="upload",
                    job_id=job.job_id,
                    progress=50,
                    step="Validating data",
                    status="running"
                )
            )
            
            # Step 3: Validate
            job.current_step = UploadJobStep.VALIDATE
            db.commit()
            UploadJobService._update_step(db, job.id, "validate", "running")
            
            df = ValidationEngine.standardize_dataframe(df, "sales")
            is_valid, errors, stats = ValidationEngine.validate_dataframe(df, "sales", f"upload:{upload.id}")
            
            job.records_failed = len(errors)
            upload.processing_progress = 80.0
            upload.processing_status = "storing"
            db.commit()
            
            UploadJobService._update_step(db, job.id, "validate", "completed")
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="upload",
                    job_id=job.job_id,
                    progress=80,
                    step="Storing data",
                    status="running"
                )
            )
            
            # Step 4: Store
            job.current_step = UploadJobStep.STORE
            db.commit()
            UploadJobService._update_step(db, job.id, "store", "running")
            
            if is_valid or len(errors) < len(df) * 0.5:
                UploadJobService._store_data(db, df, upload.id, job.id)
                job.records_processed = len(df) - len(errors)
            
            UploadJobService._update_step(db, job.id, "store", "completed")
            
            job.status = UploadJobStatus.COMPLETED
            job.progress_percentage = 100.0
            job.completed_at = datetime.utcnow()
            job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            db.commit()
            
            upload.status = "processed"
            upload.processed_at = datetime.utcnow()
            upload.processing_progress = 100.0
            upload.processing_status = "completed"
            upload.duration_seconds = job.duration_seconds
            db.commit()
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="upload",
                    job_id=job.job_id,
                    progress=100,
                    step="Completed",
                    status="completed"
                )
            )
            
            # Notification
            user = db.query(User).filter(User.id == upload.uploaded_by).first()
            if user:
                NotificationService.create_upload_notification(
                    db=db,
                    user_id=user.id,
                    filename=upload.filename,
                    success=True,
                    rows=job.records_processed,
                    message=f"Upload '{upload.filename}' processed successfully. {job.records_processed} records stored."
                )
            
        except Exception as e:
            logger.error(f"Upload job {job_id} failed: {str(e)}")
            job.status = UploadJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
            
            upload.processing_status = "failed"
            upload.status = "failed"
            db.commit()
            
            asyncio.create_task(
                manager.send_progress_update(
                    channel="upload",
                    job_id=job.job_id,
                    progress=100,
                    step="Failed",
                    status="failed"
                )
            )
            
            if upload.uploaded_by:
                user = db.query(User).filter(User.id == upload.uploaded_by).first()
                if user:
                    NotificationService.create_upload_notification(
                        db=db,
                        user_id=user.id,
                        filename=upload.filename,
                        success=False,
                        message=f"Upload '{upload.filename}' failed: {str(e)}"
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
    def _store_data(db: Session, df: pd.DataFrame, upload_id: int, job_id: int):
        """Store data in raw tables."""
        records = df.to_dict('records')
        objects_to_add = []
        
        for record in records:
            obj = RawSales(
                upload_id=upload_id,
                raw_data=record,
                validation_status="validated",
                date=record.get('date'),
                sku=record.get('sku'),
                demand=record.get('demand'),
                revenue=record.get('revenue'),
                units=record.get('units')
            )
            objects_to_add.append(obj)
        
        if objects_to_add:
            db.add_all(objects_to_add)
            db.commit()
    
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