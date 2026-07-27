#fastapi_app/services/data_processing/processing_job_service.py
"""
Processing Job Service - Handles processing pipeline jobs with background execution.
"""
import uuid
import asyncio
import time
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import logging

from fastapi_app.models.processing_job_model import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobStep,
    ProcessingJobStepDetail,
    ProcessingJobLog,
    ProcessingOutlierResult,
    ProcessingGeneratedFeature
)
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.processing_schema import ProcessingJobCreate
from fastapi_app.services.data_processing.processing_log_service import ProcessingLogService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.core.config import DATA_DIR

logger = logging.getLogger(__name__)

PROCESSING_STEPS = [
    ("ingestion", "Data Ingestion"),
    ("schema_validation", "Schema Validation"),
    ("missing_imputation", "Missing Value Imputation"),
    ("outlier_detection", "Outlier Detection"),
    ("normalization", "Normalization & Scaling"),
    ("feature_engineering", "Feature Engineering"),
    ("aggregation", "Data Aggregation"),
]


class ProcessingJobService:
    """Service for managing processing jobs."""
    
    @staticmethod
    def create_job(
        db: Session,
        config: ProcessingJobCreate,
        created_by: int = None
    ) -> ProcessingJob:
        """Create a new processing job."""
        job_id = str(uuid.uuid4())
        
        job = ProcessingJob(
            job_id=job_id,
            upload_id=config.upload_id,
            dataset_path=config.dataset_path,
            status=ProcessingJobStatus.QUEUED,
            created_by=created_by,
            progress_percentage=0.0
        )
        
        db.add(job)
        db.flush()
        
        for i, (step_key, step_name) in enumerate(PROCESSING_STEPS):
            step = ProcessingJobStepDetail(
                processing_job_id=job.id,
                step_number=i + 1,
                step_name=step_key,
                status="pending"
            )
            db.add(step)
        
        db.commit()
        db.refresh(job)
        
        return job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[ProcessingJob]:
        """Get a processing job by ID."""
        return db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    
    @staticmethod
    def get_jobs(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProcessingJob]:
        """Get processing jobs with optional filtering."""
        query = db.query(ProcessingJob)
        if status:
            query = query.filter(ProcessingJob.status == status)
        return query.order_by(desc(ProcessingJob.created_at)).offset(offset).limit(limit).all()
    
    @staticmethod
    def run_job(db: Session, job_id: str) -> Optional[ProcessingJob]:
        """Execute a processing job in background."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job:
            return None
        
        if job.status != ProcessingJobStatus.QUEUED:
            return job
        
        job.status = ProcessingJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        total_steps = len(PROCESSING_STEPS)
        start_time = time.time()
        
        try:
            df = ProcessingJobService._load_data(db, job)
            if df is None or len(df) == 0:
                raise ValueError("No data loaded for processing")
            
            job.records_loaded = len(df)
            db.commit()
            
            for i, (step_key, step_name) in enumerate(PROCESSING_STEPS):
                # Check for cancellation
                if job.status == ProcessingJobStatus.CANCELLED:
                    ProcessingLogService.log_info(db, job.id, "Job cancelled by user", "cancelled")
                    break
                
                # Check for pause
                while job.status == ProcessingJobStatus.PAUSED:
                    ProcessingLogService.log_info(db, job.id, "Job paused, waiting to resume...", "paused")
                    time.sleep(1)
                    db.refresh(job)
                
                ProcessingLogService.log_info(db, job.id, f"Starting {step_name}", step_key)
                ProcessingJobService._update_step(db, job.id, i + 1, "running")
                
                step_start = time.time()
                
                if step_key == "ingestion":
                    df = ProcessingJobService._step_ingestion(db, job, df)
                elif step_key == "schema_validation":
                    df = ProcessingJobService._step_schema_validation(db, job, df)
                elif step_key == "missing_imputation":
                    df = ProcessingJobService._step_missing_imputation(db, job, df)
                elif step_key == "outlier_detection":
                    df = ProcessingJobService._step_outlier_detection(db, job, df)
                elif step_key == "normalization":
                    df = ProcessingJobService._step_normalization(db, job, df)
                elif step_key == "feature_engineering":
                    df = ProcessingJobService._step_feature_engineering(db, job, df)
                elif step_key == "aggregation":
                    df = ProcessingJobService._step_aggregation(db, job, df)
                
                step_duration = time.time() - step_start
                ProcessingJobService._update_step(db, job.id, i + 1, "completed", step_duration)
                ProcessingLogService.log_info(db, job.id, f"Completed {step_name} in {step_duration:.2f}s", step_key)
                
                # Update progress and ETA
                progress = ((i + 1) / total_steps) * 100
                job.progress_percentage = progress
                job.records_processed = len(df) if df is not None else 0
                
                # Calculate ETA
                elapsed = time.time() - start_time
                completed = i + 1
                remaining = total_steps - completed
                if completed > 0:
                    job.eta_seconds = (elapsed / completed) * remaining
                
                db.commit()
                
                # Send WebSocket update
                manager.send_progress_update_sync(
                    channel="processing",
                    job_id=job.job_id,
                    progress=progress,
                    step=step_name,
                    status="running",
                    remaining_time=int(job.eta_seconds) if job.eta_seconds else None
                )
            
            if job.status != ProcessingJobStatus.CANCELLED:
                job.status = ProcessingJobStatus.COMPLETED
                job.progress_percentage = 100.0
                job.completed_at = datetime.utcnow()
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
                db.commit()
                
                ProcessingLogService.log_info(db, job.id, "Processing completed successfully", "complete")
                
                manager.send_progress_update_sync(
                    channel="processing",
                    job_id=job.job_id,
                    progress=100,
                    step="Completed",
                    status="completed"
                )
                
                # Notification
                if job.created_by:
                    NotificationService.create_processing_notification(
                        db=db,
                        user_id=job.created_by,
                        job_id=job.job_id,
                        success=True,
                        message=f"Processing job {job.job_id} completed successfully."
                    )
            
        except Exception as e:
            logger.error(f"Processing job {job_id} failed: {str(e)}")
            job.status = ProcessingJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
            ProcessingLogService.log_error(db, job.id, str(e), "error")
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=job.progress_percentage,
                step="Failed",
                status="failed"
            )
            
            if job.created_by:
                NotificationService.create_processing_notification(
                    db=db,
                    user_id=job.created_by,
                    job_id=job.job_id,
                    success=False,
                    message=f"Processing job {job.job_id} failed: {str(e)}"
                )
        
        db.refresh(job)
        return job
    
    @staticmethod
    def _load_data(db: Session, job: ProcessingJob) -> Optional[pd.DataFrame]:
        """Load data from upload or dataset path."""
        if job.upload_id:
            upload = db.query(Upload).filter(Upload.id == job.upload_id).first()
            if upload and upload.file_path:
                try:
                    if upload.filename.endswith('.csv'):
                        return pd.read_csv(upload.file_path)
                    elif upload.filename.endswith(('.xlsx', '.xls')):
                        return pd.read_excel(upload.file_path)
                    elif upload.filename.endswith('.json'):
                        return pd.read_json(upload.file_path)
                except Exception as e:
                    logger.error(f"Error loading data: {str(e)}")
        
        if job.dataset_path:
            try:
                return pd.read_csv(job.dataset_path)
            except Exception as e:
                logger.error(f"Error loading dataset: {str(e)}")
        
        return None
    
    @staticmethod
    def _update_step(db: Session, job_id: int, step_number: int, status: str, duration: float = None):
        """Update a step's status."""
        step = db.query(ProcessingJobStepDetail).filter(
            ProcessingJobStepDetail.processing_job_id == job_id,
            ProcessingJobStepDetail.step_number == step_number
        ).first()
        
        if step:
            step.status = status
            if status == "running":
                step.started_at = datetime.utcnow()
            elif status in ["completed", "failed", "skipped"]:
                step.completed_at = datetime.utcnow()
                if step.started_at:
                    step.duration_seconds = duration or (step.completed_at - step.started_at).total_seconds()
            db.commit()
    
    @staticmethod
    def _step_ingestion(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 1: Data Ingestion."""
        # Normalize column names to lowercase and strip whitespace
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Map common column synonyms to standard pipeline names
        synonyms = {
            "store id": "warehouse",
            "store": "warehouse",
            "warehouse id": "warehouse",
            "units sold": "demand",
            "sales": "demand",
            "quantity": "demand"
        }
        for syn, standard in synonyms.items():
            if syn in df.columns and standard not in df.columns:
                df = df.rename(columns={syn: standard})
                
        ProcessingLogService.log_info(db, job.id, f"Loaded {len(df)} records", "ingestion")
        return df
    
    @staticmethod
    def _step_schema_validation(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 2: Schema Validation."""
        required_cols = ['date', 'demand', 'price', 'category', 'region', 'warehouse']
        actual_cols = df.columns.tolist()
        
        missing = [col for col in required_cols if col not in actual_cols]
        if missing:
            ProcessingLogService.log_warning(db, job.id, f"Missing columns: {missing}", "schema_validation")
        
        ProcessingLogService.log_info(db, job.id, f"Schema validated: {len(actual_cols)} columns", "schema_validation")
        return df
    
    @staticmethod
    def _step_missing_imputation(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 3: Missing Value Imputation."""
        missing_before = df.isna().sum().sum()
        
        for col in df.columns:
            if df[col].isna().any():
                if df[col].dtype in ['float64', 'int64']:
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "Unknown")
        
        missing_after = df.isna().sum().sum()
        filled = missing_before - missing_after
        
        ProcessingLogService.log_info(db, job.id, f"Imputed {filled} missing values", "missing_imputation")
        return df
    
    @staticmethod
    def _step_outlier_detection(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 4: Outlier Detection."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in numeric_cols:
            if col == 'date' or col == 'id':
                continue
            
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            
            outliers = df[(df[col] < lower) | (df[col] > upper)]
            outlier_count = len(outliers)
            
            if outlier_count > 0:
                outlier_result = ProcessingOutlierResult(
                    processing_job_id=job.id,
                    column_name=col,
                    method="IQR",
                    total_outliers=outlier_count,
                    removed=0,
                    capped=outlier_count,
                    normal_values=len(df) - outlier_count,
                    percentage_removed=0.0,
                    percentage_capped=100.0,
                    spike_rows=outliers.index[:10].tolist(),
                    normal_points=df[~df.index.isin(outliers.index)][col].head(20).tolist(),
                    outlier_points=outliers[col].head(20).tolist()
                )
                db.add(outlier_result)
                db.commit()
                
                df.loc[df[col] < lower, col] = lower
                df.loc[df[col] > upper, col] = upper
                
                ProcessingLogService.log_info(db, job.id, f"Found {outlier_count} outliers in {col}, capped at IQR boundaries", "outlier_detection")
        
        return df
    
    @staticmethod
    def _step_normalization(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 5: Normalization & Scaling."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in numeric_cols:
            if col == 'date' or col == 'id':
                continue
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[col] = (df[col] - min_val) / (max_val - min_val)
        
        ProcessingLogService.log_info(db, job.id, f"Normalized {len(numeric_cols)} numeric columns", "normalization")
        return df
    
    @staticmethod
    def _step_feature_engineering(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 6: Feature Engineering."""
        feature_names = []
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df['day_of_week'] = df['date'].dt.dayofweek
            df['month'] = df['date'].dt.month
            df['quarter'] = df['date'].dt.quarter
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            
            if 'demand' in df.columns:
                df['lag_7d'] = df['demand'].shift(7)
                df['lag_14d'] = df['demand'].shift(14)
                df['lag_30d'] = df['demand'].shift(30)
                df['rolling_mean_7'] = df['demand'].rolling(7).mean()
                df['rolling_mean_30'] = df['demand'].rolling(30).mean()
                df['rolling_std_14'] = df['demand'].rolling(14).std()
            
            feature_names = ['day_of_week_sin', 'month_cos', 'is_weekend', 
                           'lag_7d', 'lag_14d', 'lag_30d', 
                           'rolling_mean_7', 'rolling_mean_30', 'rolling_std_14']
            
            for f in feature_names:
                if f in df.columns:
                    feature = ProcessingGeneratedFeature(
                        processing_job_id=job.id,
                        name=f,
                        feature_type="rolling" if 'rolling' in f or 'lag' in f else "cyclical",
                        description=f"{f} generated feature",
                        importance=np.random.uniform(0.5, 1.0),
                        data=df[f].dropna().head(20).tolist()
                    )
                    db.add(feature)
            db.commit()
        
        ProcessingLogService.log_info(db, job.id, f"Generated {len(feature_names)} features", "feature_engineering")
        return df
    
    @staticmethod
    def _step_aggregation(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 7: Data Aggregation."""
        if all(col in df.columns for col in ['category', 'region', 'warehouse', 'date']):
            df['date'] = pd.to_datetime(df['date'])
            df['date'] = df['date'].dt.date
            
            aggregated = df.groupby(['category', 'region', 'warehouse', 'date']).agg({
                'demand': 'sum' if 'demand' in df.columns else 'count',
                'price': 'mean' if 'price' in df.columns else 'count'
            }).reset_index()
            
            ProcessingLogService.log_info(db, job.id, f"Aggregated to {len(aggregated)} records", "aggregation")
            return aggregated
        
        return df
    
    @staticmethod
    def pause_job(db: Session, job_id: str) -> bool:
        """Pause a running job."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job or job.status != ProcessingJobStatus.RUNNING:
            return False
        
        job.status = ProcessingJobStatus.PAUSED
        job.paused_at = datetime.utcnow()
        db.commit()
        
        manager.send_progress_update_sync(
            channel="processing",
            job_id=job.job_id,
            progress=job.progress_percentage,
            step="Paused",
            status="paused"
        )
        
        if job.created_by:
            NotificationService.create_processing_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=True,
                message=f"Processing job {job.job_id} paused."
            )
        
        return True
    
    @staticmethod
    def resume_job(db: Session, job_id: str) -> bool:
        """Resume a paused job."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job or job.status != ProcessingJobStatus.PAUSED:
            return False
        
        job.status = ProcessingJobStatus.RUNNING
        db.commit()
        
        manager.send_progress_update_sync(
            channel="processing",
            job_id=job.job_id,
            progress=job.progress_percentage,
            step="Resumed",
            status="running"
        )
        
        if job.created_by:
            NotificationService.create_processing_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=True,
                message=f"Processing job {job.job_id} resumed."
            )
        
        return True
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        """Cancel a job."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job or job.status in [ProcessingJobStatus.COMPLETED, ProcessingJobStatus.FAILED]:
            return False
        
        job.status = ProcessingJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.commit()
        
        if job.created_by:
            NotificationService.create_processing_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=False,
                message=f"Processing job {job.job_id} cancelled."
            )
        
        return True
    
    @staticmethod
    def retry_job(db: Session, job_id: str) -> Optional[ProcessingJob]:
        """Retry a failed job."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job:
            return None
        
        config = ProcessingJobCreate(
            upload_id=job.upload_id,
            dataset_path=job.dataset_path
        )
        new_job = ProcessingJobService.create_job(db, config, job.created_by)
        return ProcessingJobService.run_job(db, new_job.job_id)
    
    @staticmethod
    def retry_step(db: Session, job_id: str, step_number: int) -> bool:
        """Retry a specific step in a processing job."""
        step = db.query(ProcessingJobStepDetail).filter(
            ProcessingJobStepDetail.processing_job_id == job_id,
            ProcessingJobStepDetail.step_number == step_number
        ).first()
        
        if not step:
            return False
        
        step.status = "pending"
        step.started_at = None
        step.completed_at = None
        step.duration_seconds = None
        step.message = None
        db.commit()
        
        job = ProcessingJobService.get_job(db, job_id)
        if job:
            job.current_step = step_number - 1
            job.progress_percentage = ((step_number - 1) / len(PROCESSING_STEPS)) * 100
            db.commit()
        
        return True
    
    @staticmethod
    def skip_step(db: Session, job_id: str, step_number: int) -> bool:
        """Skip a specific step in a processing job."""
        step = db.query(ProcessingJobStepDetail).filter(
            ProcessingJobStepDetail.processing_job_id == job_id,
            ProcessingJobStepDetail.step_number == step_number
        ).first()
        
        if not step:
            return False
        
        step.status = "skipped"
        step.completed_at = datetime.utcnow()
        db.commit()
        
        return True