from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from fastapi_app.models.forecast_model import Forecast
from fastapi_app.schemas.forecast_schema import (
    ForecastCreate,
    ForecastResponse,
    MetricsResponse,
)
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import uuid

# Mock registry for model management
MODEL_REGISTRY: Dict[str, Any] = {}


class ForecastModelService:
    """Manages forecast model lifecycle"""

    @staticmethod
    def get_all_models() -> List[Dict[str, Any]]:
        """Get all registered models"""
        return list(MODEL_REGISTRY.values())

    @staticmethod
    def create_model(name: str, model_type: str, version: str) -> Dict[str, Any]:
        """Create and register a new model"""
        model_id = str(uuid.uuid4())
        model_data = {
            "id": model_id,
            "name": name,
            "model_type": model_type,
            "version": version,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }
        MODEL_REGISTRY[model_id] = model_data
        return model_data

    @staticmethod
    def update_model(model_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update an existing model"""
        if model_id in MODEL_REGISTRY:
            MODEL_REGISTRY[model_id].update(kwargs)
            return MODEL_REGISTRY[model_id]
        return None

    @staticmethod
    def delete_model(model_id: str) -> bool:
        """Delete a model from registry"""
        if model_id in MODEL_REGISTRY:
            del MODEL_REGISTRY[model_id]
            return True
        return False

    @staticmethod
    def get_model(model_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific model"""
        return MODEL_REGISTRY.get(model_id)


class ForecastTrainingService:
    """Manages training jobs"""

    TRAINING_JOBS: Dict[str, Any] = {}

    @staticmethod
    def start_training_job(model_type: str, csv_path: Optional[str] = None) -> Dict[str, Any]:
        """Start a new training job"""
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "model_type": model_type,
            "status": "in_progress",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metrics": None,
        }
        ForecastTrainingService.TRAINING_JOBS[job_id] = job_data
        return job_data

    @staticmethod
    def get_training_job_status(job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a training job"""
        job = ForecastTrainingService.TRAINING_JOBS.get(job_id)
        if job:
            # Simulate job completion after 5 seconds
            if (
                datetime.fromisoformat(job["created_at"]) + timedelta(seconds=5)
                < datetime.utcnow()
            ):
                job["status"] = "completed"
                job["metrics"] = {
                    "mae": 15.5,
                    "rmse": 22.3,
                    "mape": 8.5,
                    "accuracy": 91.2,
                }
        return job

    @staticmethod
    def complete_training_job(job_id: str, metrics: Dict) -> bool:
        """Mark a training job as complete"""
        if job_id in ForecastTrainingService.TRAINING_JOBS:
            ForecastTrainingService.TRAINING_JOBS[job_id]["status"] = "completed"
            ForecastTrainingService.TRAINING_JOBS[job_id]["metrics"] = metrics
            return True
        return False


class ForecastGenerationService:
    """Manages forecast generation"""

    @staticmethod
    def generate_forecast(
        db: Session,
        forecast_data: ForecastCreate,
    ) -> Forecast:
        """Generate and store a forecast"""
        db_forecast = Forecast(**forecast_data.dict())
        db.add(db_forecast)
        db.commit()
        db.refresh(db_forecast)
        return db_forecast

    @staticmethod
    def get_forecast_results(db: Session, limit: int = 100, offset: int = 0) -> List[Forecast]:
        """Get all forecast results with pagination"""
        return db.query(Forecast).order_by(desc(Forecast.forecast_date)).offset(offset).limit(limit).all()

    @staticmethod
    def get_forecast_by_id(db: Session, forecast_id: int) -> Optional[Forecast]:
        """Get a specific forecast"""
        return db.query(Forecast).filter(Forecast.id == forecast_id).first()

    @staticmethod
    def get_forecasts_by_sku(db: Session, sku: str) -> List[Forecast]:
        """Get all forecasts for a specific SKU"""
        return db.query(Forecast).filter(Forecast.sku == sku).order_by(desc(Forecast.forecast_date)).all()

    @staticmethod
    def get_forecasts_by_region(db: Session, region: str) -> List[Forecast]:
        """Get all forecasts for a specific region"""
        return db.query(Forecast).filter(Forecast.region == region).order_by(desc(Forecast.forecast_date)).all()


class ForecastMetricsService:
    """Manages forecast metrics and performance"""

    @staticmethod
    def get_metrics(db: Session) -> Dict[str, Any]:
        """Get overall forecast metrics"""
        total_forecasts = db.query(func.count(Forecast.id)).scalar() or 0
        avg_confidence = (
            db.query(func.avg(Forecast.confidence_score)).scalar() or 0
        )

        # Get metrics by model type
        model_metrics = (
            db.query(
                Forecast.model_used,
                func.count(Forecast.id).label("count"),
                func.avg(Forecast.confidence_score).label("avg_confidence"),
            )
            .group_by(Forecast.model_used)
            .all()
        )

        model_stats = [
            {
                "model": m[0],
                "forecast_count": m[1],
                "avg_confidence": float(m[2]) if m[2] else 0,
            }
            for m in model_metrics
        ]

        return {
            "total_forecasts": total_forecasts,
            "average_confidence": float(avg_confidence) if avg_confidence else 0,
            "model_stats": model_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def get_model_metrics(db: Session, model_type: str) -> Dict[str, Any]:
        """Get metrics for a specific model"""
        forecasts = db.query(Forecast).filter(Forecast.model_used == model_type).all()

        if not forecasts:
            return {
                "model_type": model_type,
                "total_forecasts": 0,
                "average_confidence": 0,
            }

        confidences = [f.confidence_score for f in forecasts if f.confidence_score]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "model_type": model_type,
            "total_forecasts": len(forecasts),
            "average_confidence": float(avg_confidence),
            "forecast_range": {
                "min": min(f.predicted_demand for f in forecasts),
                "max": max(f.predicted_demand for f in forecasts),
                "avg": sum(f.predicted_demand for f in forecasts) / len(forecasts),
            },
        }


class ForecastRetrainingService:
    """Manages model retraining"""

    @staticmethod
    def retrain_model(db: Session, model_id: str) -> Dict[str, Any]:
        """Retrain a specific model"""
        job = ForecastTrainingService.start_training_job("retrain")
        return {
            "job_id": job["job_id"],
            "model_id": model_id,
            "status": "initiated",
            "message": f"Retraining started for model {model_id}",
        }

    @staticmethod
    def retrain_all_models(db: Session) -> Dict[str, Any]:
        """Retrain all models"""
        jobs = []
        for model_id, model_data in MODEL_REGISTRY.items():
            job = ForecastTrainingService.start_training_job(model_data["model_type"])
            jobs.append({
                "job_id": job["job_id"],
                "model_id": model_id,
                "model_type": model_data["model_type"],
            })

        return {
            "total_jobs": len(jobs),
            "jobs": jobs,
            "message": f"Retraining initiated for {len(jobs)} models",
        }

    @staticmethod
    def get_retraining_status(job_id: str) -> Optional[Dict[str, Any]]:
        """Get retraining job status"""
        return ForecastTrainingService.get_training_job_status(job_id)
