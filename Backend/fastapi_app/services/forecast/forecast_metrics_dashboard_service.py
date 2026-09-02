# fastapi_app/services/forecast/forecast_metrics_dashboard_service.py
"""
Forecast Metrics Dashboard Service - Aggregates metrics from real data only.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta

from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.models.training_job_model import TrainingHistory
from fastapi_app.models.forecast_metric_history_model import ForecastMetricHistory
from fastapi_app.models.forecast_job_model import ForecastResult


class ForecastMetricsDashboardService:
    """Service for forecast metrics dashboard - uses real data only."""
    
    @staticmethod
    def get_metrics_history(
        db: Session,
        days: int = 30,
        model_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get historical metrics from real data."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(ForecastMetricHistory).filter(
            ForecastMetricHistory.date >= start_date
        )
        if model_type:
            query = query.filter(ForecastMetricHistory.model_type == model_type)
        
        history = query.order_by(ForecastMetricHistory.date).all()
        
        if not history:
            # ✅ Return empty list instead of fake data
            return []
        
        return [
            {
                "date": h.date.strftime("%Y-%m-%d"),
                "accuracy": h.accuracy or 0,
                "rmse": h.rmse or 0,
                "mae": h.mae or 0,
                "mape": h.mape or 0,
                "r2": h.r2 or 0
            }
            for h in history
        ]
    
    @staticmethod
    def get_metrics_comparison(db: Session) -> List[Dict[str, Any]]:
        """Get comparison metrics across model types from real data."""
        # ✅ Get latest metrics per model type from ModelRegistry
        model_types = db.query(ModelRegistry.model_type).distinct().all()
        
        comparisons = []
        for mt in model_types:
            model_type = mt[0]
            model = db.query(ModelRegistry).filter(
                ModelRegistry.model_type == model_type,
                ModelRegistry.is_active == True,
                ModelRegistry.best_accuracy.isnot(None)
            ).order_by(desc(ModelRegistry.last_trained)).first()
            
            if model and model.best_accuracy is not None:
                comparisons.append({
                    "name": model_type.upper(),
                    "accuracy": model.best_accuracy or 0,
                    "rmse": model.best_rmse or 0,
                    "mae": model.best_mae or 0,
                    "mape": model.best_mape or 0,
                    "r2": model.best_r2 or 0
                })
        
        return comparisons
    
    @staticmethod
    def get_best_model(db: Session, sku: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the best performing model from real data (optionally filtered by SKU)."""
        from fastapi_app.models.forecast_job_model import ForecastJob, ForecastJobStatus
        
        if sku and sku != "default":
            # Query completed forecast jobs for this SKU that have model registry links
            jobs = db.query(ForecastJob).filter(
                ForecastJob.sku == sku,
                ForecastJob.status == ForecastJobStatus.COMPLETED,
                ForecastJob.model_registry_id.isnot(None)
            ).all()
            
            if jobs:
                # Find the job with the highest accuracy
                best_job = max(
                    [j for j in jobs if j.metrics and "accuracy" in j.metrics],
                    key=lambda j: j.metrics.get("accuracy", 0.0),
                    default=None
                )
                if best_job:
                    model = db.query(ModelRegistry).filter(ModelRegistry.id == best_job.model_registry_id).first()
                    if model:
                        return {
                            "id": model.id,
                            "name": model.name,
                            "model_type": model.model_type,
                            "accuracy": best_job.metrics.get("accuracy"),
                            "rmse": best_job.metrics.get("rmse"),
                            "mae": best_job.metrics.get("mae"),
                            "mape": best_job.metrics.get("mape"),
                            "r2": best_job.metrics.get("r2"),
                            "last_trained": model.last_trained.isoformat() if model.last_trained else None
                        }
                        
        # Fallback/Default: Get active model registry entry with highest overall accuracy
        model = db.query(ModelRegistry).filter(
            ModelRegistry.is_active == True,
            ModelRegistry.best_accuracy.isnot(None)
        ).order_by(desc(ModelRegistry.best_accuracy)).first()
        
        if not model:
            return None
        
        return {
            "id": model.id,
            "name": model.name,
            "model_type": model.model_type,
            "accuracy": model.best_accuracy,
            "rmse": model.best_rmse,
            "mae": model.best_mae,
            "mape": model.best_mape,
            "r2": model.best_r2,
            "last_trained": model.last_trained.isoformat() if model.last_trained else None
        }