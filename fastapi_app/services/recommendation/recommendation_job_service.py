#fastapi_app/services/recommendation_job_service.py
"""
Recommendation Job Service - Manages recommendation job lifecycle.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastapi_app.models.recommendation_job_model import (
    RecommendationJob,
    RecommendationJobStatus,
    RecommendationJobStep,
    RecommendationJobStepDetail
)
from fastapi_app.models.forecast_job_model import ForecastJob

import logging
logger = logging.getLogger(__name__)

# Step definitions
RECOMMENDATION_STEPS = [
    (1, "loading_forecast", "Loading Forecast"),
    (2, "loading_summary", "Loading Forecast Summary"),
    (3, "reading_results", "Reading Forecast Results"),
    (4, "demand_analysis", "Demand Analysis"),
    (5, "inventory_analysis", "Inventory Analysis"),
    (6, "risk_analysis", "Risk Analysis"),
    (7, "generating_recommendations", "Generating Recommendations"),
    (8, "removing_duplicates", "Removing Duplicates"),
    (9, "validating", "Validating Recommendations"),
    (10, "saving_recommendations", "Saving Recommendations"),
    (11, "notifying", "Sending Notifications"),
    (12, "refreshing_dashboard", "Refreshing Dashboard"),
]


class RecommendationJobService:
    """Service for managing recommendation jobs."""
    
    @staticmethod
    def create_job(
        db: Session,
        forecast_job_id: str,
        forecast_summary: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None
    ) -> Optional[RecommendationJob]:
        """Create a new recommendation job from a forecast."""
        # Get forecast job
        forecast_job = db.query(ForecastJob).filter(
            ForecastJob.job_id == forecast_job_id
        ).first()
        
        if not forecast_job:
            logger.error(f"Forecast job {forecast_job_id} not found")
            return None
        
        if forecast_job.status != "completed":
            logger.warning(f"Forecast job {forecast_job_id} is not completed")
            return None
        
        # Check if job already exists
        existing = db.query(RecommendationJob).filter(
            RecommendationJob.forecast_job_id == forecast_job_id
        ).first()
        
        if existing:
            return existing
        
        # Create job
        job = RecommendationJob(
            job_id=str(uuid.uuid4()),
            forecast_job_id=forecast_job_id,
            forecast_job_internal_id=forecast_job.id,
            status=RecommendationJobStatus.QUEUED,
            created_by=created_by,
            forecast_summary=forecast_summary,
            progress_percentage=0.0
        )
        
        db.add(job)
        db.flush()
        
        # Create steps
        for step_num, step_name_enum, step_name in RECOMMENDATION_STEPS:
            step = RecommendationJobStepDetail(
                recommendation_job_id=job.id,
                step_number=step_num,
                step_name=step_name_enum,
                status="pending"
            )
            db.add(step)
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Created recommendation job {job.job_id} for forecast {forecast_job_id}")
        return job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[RecommendationJob]:
        """Get a recommendation job by ID."""
        return db.query(RecommendationJob).filter(
            RecommendationJob.job_id == job_id
        ).first()
    
    @staticmethod
    def get_jobs(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RecommendationJob]:
        """Get recommendation jobs with optional filtering."""
        query = db.query(RecommendationJob)
        if status:
            query = query.filter(RecommendationJob.status == status)
        return query.order_by(desc(RecommendationJob.created_at)).offset(offset).limit(limit).all()
    
    @staticmethod
    def update_progress(
        db: Session,
        job_id: int,
        progress: float,
        current_step: int,
        step_name: str,
        message: Optional[str] = None
    ):
        """Update job progress."""
        job = db.query(RecommendationJob).filter(RecommendationJob.id == job_id).first()
        if not job:
            return
        
        job.progress_percentage = progress
        job.current_step = current_step
        job.current_step_name = step_name
        if message:
            job.current_step_message = message
        
        db.commit()
        db.refresh(job)
    
    @staticmethod
    def update_step(
        db: Session,
        job_id: int,
        step_number: int,
        status: str,
        duration: Optional[float] = None,
        message: Optional[str] = None
    ) -> Optional[RecommendationJobStepDetail]:
        """Update a job step."""
        step = db.query(RecommendationJobStepDetail).filter(
            RecommendationJobStepDetail.recommendation_job_id == job_id,
            RecommendationJobStepDetail.step_number == step_number
        ).first()
        
        if not step:
            return None
        
        step.status = status
        if status == "running":
            step.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            step.completed_at = datetime.utcnow()
            if step.started_at:
                step.duration_seconds = duration or (step.completed_at - step.started_at).total_seconds()
        if message:
            step.message = message
        
        db.commit()
        db.refresh(step)
        return step
    
    @staticmethod
    def pause_job(db: Session, job_id: str) -> bool:
        """Pause a running job."""
        job = RecommendationJobService.get_job(db, job_id)
        if not job or job.status != RecommendationJobStatus.RUNNING:
            return False
        
        job.status = RecommendationJobStatus.PAUSED
        job.paused_at = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def resume_job(db: Session, job_id: str) -> bool:
        """Resume a paused job."""
        job = RecommendationJobService.get_job(db, job_id)
        if not job or job.status != RecommendationJobStatus.PAUSED:
            return False
        
        job.status = RecommendationJobStatus.RUNNING
        job.paused_at = None
        db.commit()
        return True
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        """Cancel a running or queued job."""
        job = RecommendationJobService.get_job(db, job_id)
        if not job or job.status not in [
            RecommendationJobStatus.QUEUED,
            RecommendationJobStatus.RUNNING
        ]:
            return False
        
        job.status = RecommendationJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def complete_job(
        db: Session,
        job_id: str,
        total_recommendations: int,
        saved_recommendations: int,
        recommendation_score: float = 0,
        metrics: Optional[Dict] = None
    ) -> bool:
        """Mark a job as completed."""
        job = RecommendationJobService.get_job(db, job_id)
        if not job:
            return False
        
        job.status = RecommendationJobStatus.COMPLETED
        job.progress_percentage = 100.0
        job.completed_at = datetime.utcnow()
        job.total_recommendations = total_recommendations
        job.saved_recommendations = saved_recommendations
        job.recommendation_score = recommendation_score
        job.elapsed_time = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
        job.total_processing_time = job.elapsed_time
        job.job_duration = job.elapsed_time
        if metrics:
            job.metrics = metrics
        db.commit()
        return True
    
    @staticmethod
    def fail_job(
        db: Session,
        job_id: str,
        error_message: str,
        failed_step: int = None,
        failed_step_name: str = None
    ) -> bool:
        """Mark a job as failed."""
        job = RecommendationJobService.get_job(db, job_id)
        if not job:
            return False
        
        job.status = RecommendationJobStatus.FAILED
        job.completed_at = datetime.utcnow()
        job.error_message = error_message
        job.failed_step = failed_step or job.current_step
        job.failed_step_name = failed_step_name or job.current_step_name
        job.elapsed_time = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
        db.commit()
        return True
    
    @staticmethod
    def retry_job(db: Session, job_id: str) -> Optional[RecommendationJob]:
        """Retry a failed job."""
        old_job = RecommendationJobService.get_job(db, job_id)
        if not old_job:
            return None
        
        # Create new job
        new_job = RecommendationJobService.create_job(
            db=db,
            forecast_job_id=old_job.forecast_job_id,
            forecast_summary=old_job.forecast_summary,
            created_by=old_job.created_by
        )
        
        return new_job