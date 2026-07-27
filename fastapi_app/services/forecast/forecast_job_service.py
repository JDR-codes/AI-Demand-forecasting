# fastapi_app/services/forecast/forecast_job_service.py
"""
Forecast Job Service - CRUD operations only.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
import logging

from fastapi_app.models.forecast_job_model import (
    ForecastJob,
    ForecastJobStatus,
    ForecastJobStep,
    ForecastJobStepDetail,  # ✅ Correct model
    ForecastResult
)
from fastapi_app.schemas.forecast_schema import ForecastJobCreate

logger = logging.getLogger(__name__)


class ForecastJobService:
    """Service for managing forecast jobs - CRUD only."""
    
    # Step definitions with enum values
    JOB_STEPS = [
        (1, ForecastJobStep.LOADING_DATA, "Loading Dataset"),
        (2, ForecastJobStep.VALIDATING_DATA, "Validating Dataset"),
        (3, ForecastJobStep.LOADING_MODEL, "Loading Model"),
        (4, ForecastJobStep.RUNNING_MODEL, "Running Model"),
        (5, ForecastJobStep.GENERATING_OUTPUT, "Generating Output"),
        (6, ForecastJobStep.SAVING_RESULTS, "Saving Results"),
    ]
    
    @staticmethod
    def create_job(
        db: Session,
        config: ForecastJobCreate,
        created_by: int = None
    ) -> ForecastJob:
        """Create a new forecast job."""
        from fastapi_app.models.model_registry_model import ModelRegistry
        from fastapi import HTTPException
        
        # Resolve model registry ID
        model_id = config.model_registry_id
        if not model_id or model_id in ["", "string", "default"]:
            default_model = db.query(ModelRegistry).filter(ModelRegistry.is_default == True).first()
            if not default_model:
                default_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
            
            if default_model:
                model_id = default_model.id
            else:
                # Auto-seed a default registered model if none exists
                try:
                    default_model = ModelRegistry(
                        name="Default ARIMA Model",
                        model_type="arima",
                        version="v1",
                        is_default=True,
                        is_active=True,
                        status="active",
                        description="Default system-generated ARIMA model."
                    )
                    db.add(default_model)
                    db.commit()
                    db.refresh(default_model)
                    model_id = default_model.id
                except Exception as e:
                    logger.error(f"Failed to auto-seed default model: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail="No registered models found. Please train and register a model first."
                    )
        else:
            # Validate user-provided model ID exists
            model_exists = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
            if not model_exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"Model registry entry with ID '{model_id}' does not exist. Please specify a valid model registry ID."
                )

        job_id = str(uuid.uuid4())
        
        configuration = config.configuration or {}
        configuration.update({
            "sku": config.sku or "default",
            "region": config.region,
            "warehouse": config.warehouse,
            "unit_price": configuration.get("unit_price", 30.0)
        })
        
        job = ForecastJob(
            job_id=job_id,
            upload_id=config.upload_id,
            model_registry_id=model_id,
            forecast_horizon=config.forecast_horizon or 7,
            configuration=configuration,
            sku=config.sku or "default",
            region=config.region,
            warehouse=config.warehouse,
            status=ForecastJobStatus.QUEUED,
            created_by=created_by,
            current_step=0,
            progress_percentage=0.0
        )
        
        db.add(job)
        db.flush()
        
        # ✅ Create job steps using ForecastJobStepDetail (SQLAlchemy model)
        for step_num, step_enum, step_name in ForecastJobService.JOB_STEPS:
            step = ForecastJobStepDetail(
                forecast_job_id=job.id,
                step_number=step_num,
                step_name=step_enum,
                status="pending"
            )
            db.add(step)
        
        db.commit()
        db.refresh(job)
        
        return job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[ForecastJob]:
        """Get a forecast job by ID with eager loading."""
        return db.query(ForecastJob).options(
            joinedload(ForecastJob.job_steps),
            joinedload(ForecastJob.forecast_results)
        ).filter(ForecastJob.job_id == job_id).first()
    
    @staticmethod
    def get_jobs(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ForecastJob]:
        """Get forecast jobs with optional filtering."""
        query = db.query(ForecastJob)
        
        if status:
            query = query.filter(ForecastJob.status == status)
        
        return query.order_by(desc(ForecastJob.created_at)).offset(offset).limit(limit).all()
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        """Cancel a queued or running job."""
        job = ForecastJobService.get_job(db, job_id)
        if not job:
            return False
        
        if job.status in [ForecastJobStatus.QUEUED, ForecastJobStatus.RUNNING]:
            job.status = ForecastJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def get_job_results(db: Session, job_id: int) -> List[ForecastResult]:
        """Get results for a forecast job by internal ID."""
        return db.query(ForecastResult).filter(
            ForecastResult.forecast_job_id == job_id
        ).order_by(ForecastResult.forecast_date).all()
    
    @staticmethod
    def get_job_results_by_job_id(db: Session, job_id: str) -> List[ForecastResult]:
        """Get results for a forecast job by job_id."""
        job = ForecastJobService.get_job(db, job_id)
        if not job:
            return []
        return ForecastJobService.get_job_results(db, job.id)