# fastapi_app/services/forecast/forecast_dashboard_service.py
"""
Forecast Dashboard Service - Aggregates dashboard data with metrics.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from fastapi_app.models.forecast_job_model import ForecastJob, ForecastJobStatus, ForecastResult
from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.models.training_job_model import TrainingJob
from fastapi_app.services.forecast.forecast_job_service import ForecastJobService
from fastapi_app.schemas.forecast_schema import ForecastDashboardSummary


class ForecastDashboardService:
    """Service for forecast dashboard data."""
    
    @staticmethod
    def get_summary(db: Session, model_type: str = None) -> Dict[str, Any]:
        """Get dashboard summary metrics."""
        total_jobs = db.query(func.count(ForecastJob.id)).scalar() or 0
        completed_jobs = db.query(func.count(ForecastJob.id)).filter(
            ForecastJob.status == ForecastJobStatus.COMPLETED
        ).scalar() or 0
        failed_jobs = db.query(func.count(ForecastJob.id)).filter(
            ForecastJob.status == ForecastJobStatus.FAILED
        ).scalar() or 0
        running_jobs = db.query(func.count(ForecastJob.id)).filter(
            ForecastJob.status == ForecastJobStatus.RUNNING
        ).scalar() or 0
        queued_jobs = db.query(func.count(ForecastJob.id)).filter(
            ForecastJob.status == ForecastJobStatus.QUEUED
        ).scalar() or 0
        
        total_forecasts = db.query(func.count(ForecastResult.id)).scalar() or 0
        
        # Active models
        models_query = db.query(ModelRegistry).filter(ModelRegistry.is_active == True)
        if model_type:
            models_query = models_query.filter(ModelRegistry.model_type == model_type)
        models = models_query.all()
        active_models = len(models)
        total_models = db.query(func.count(ModelRegistry.id)).scalar() or 0
        
        # ✅ Average metrics across all models
        avg_accuracy = db.query(func.avg(ModelRegistry.best_accuracy)).scalar()
        avg_rmse = db.query(func.avg(ModelRegistry.best_rmse)).scalar()
        avg_mae = db.query(func.avg(ModelRegistry.best_mae)).scalar()
        avg_mape = db.query(func.avg(ModelRegistry.best_mape)).scalar()
        
        # ✅ Latest training
        latest_training = db.query(TrainingJob).filter(
            TrainingJob.status == "completed"
        ).order_by(desc(TrainingJob.completed_at)).first()
        
        # ✅ Best model
        best_model = db.query(ModelRegistry).filter(
            ModelRegistry.is_active == True,
            ModelRegistry.best_accuracy.isnot(None)
        ).order_by(desc(ModelRegistry.best_accuracy)).first()
        
        # Recent jobs
        recent_jobs = db.query(ForecastJob).options(
            joinedload(ForecastJob.forecast_results)
        ).order_by(desc(ForecastJob.created_at)).limit(10).all()
        
        return ForecastDashboardSummary(
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            running_jobs=running_jobs,
            queued_jobs=queued_jobs,
            total_forecasts=total_forecasts,
            active_models=active_models,
            total_models=total_models,
            average_accuracy=float(avg_accuracy) if avg_accuracy else None,
            average_rmse=float(avg_rmse) if avg_rmse else None,
            average_mae=float(avg_mae) if avg_mae else None,
            average_mape=float(avg_mape) if avg_mape else None,
            latest_training=latest_training.completed_at if latest_training else None,
            best_model={
                "id": best_model.id,
                "name": best_model.name,
                "model_type": best_model.model_type,
                "accuracy": best_model.best_accuracy,
                "rmse": best_model.best_rmse,
                "mae": best_model.best_mae
            } if best_model else None
        )
    
    @staticmethod
    def get_job_results(db: Session, job_id: str) -> Dict[str, Any]:
        """Get results for a specific job."""
        job = ForecastJobService.get_job(db, job_id)
        if not job:
            return {"error": "Job not found"}
        
        results = ForecastJobService.get_job_results(db, job.id)
        
        return {
            "job": {
                "id": job.job_id,
                "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
                "progress": job.progress_percentage,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            },
            "results": [
                {
                    "date": r.forecast_date.isoformat() if r.forecast_date else None,
                    "prediction": r.prediction,
                    "sku": r.sku,
                    "confidence_score": r.confidence_score,
                    "is_peak": r.is_peak,
                    "is_forecast": r.is_forecast,
                    "confidence_upper": r.confidence_upper,
                    "confidence_lower": r.confidence_lower
                }
                for r in results
            ],
            "metrics": job.metrics,
            "error_message": job.error_message
        }