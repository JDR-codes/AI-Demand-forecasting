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

from fastapi_app.db.session import SessionLocal
from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.models.training_job_model import TrainingJob


class ForecastModelService:
    """Manages forecast model lifecycle (persisted in DB)"""

    @staticmethod
    def get_all_models() -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            rows = db.query(ModelRegistry).order_by(ModelRegistry.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "model_type": r.model_type,
                    "version": r.version,
                    "status": r.status,
                    "path": r.path,
                    "meta_info": r.meta_info,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()

    @staticmethod
    def create_model(name: str, model_type: str, version: str, path: Optional[str] = None, metadata: Optional[dict] = None) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            model = ModelRegistry(name=name, model_type=model_type, version=version, path=path, meta_info=metadata or {}, status="active")
            db.add(model)
            db.commit()
            db.refresh(model)
            return {
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "version": model.version,
                "status": model.status,
                "path": model.path,
                "meta_info": model.meta_info,
                "created_at": model.created_at.isoformat() if model.created_at else None,
            }
        finally:
            db.close()

    @staticmethod
    def update_model(model_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            model = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
            if not model:
                return None
            for k, v in kwargs.items():
                if hasattr(model, k):
                    setattr(model, k, v)
            db.commit()
            db.refresh(model)
            return {
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "version": model.version,
                "status": model.status,
                "path": model.path,
                "meta_info": model.meta_info,
                "created_at": model.created_at.isoformat() if model.created_at else None,
            }
        finally:
            db.close()

    @staticmethod
    def delete_model(model_id: str) -> bool:
        db = SessionLocal()
        try:
            model = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
            if not model:
                return False
            db.delete(model)
            db.commit()
            return True
        finally:
            db.close()

    @staticmethod
    def get_model(model_id: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            model = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
            if not model:
                return None
            return {
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "version": model.version,
                "status": model.status,
                "path": model.path,
                "meta_info": model.meta_info,
                "created_at": model.created_at.isoformat() if model.created_at else None,
            }
        finally:
            db.close()


class ForecastTrainingService:
    """Manages training jobs persisted in DB"""

    MODEL_TYPE_METRICS = {
        "arima": {
            "mae": 15.5,
            "rmse": 22.3,
            "mape": 8.5,
            "accuracy": 91.2,
        },
        "xgboost": {
            "mae": 12.8,
            "rmse": 18.9,
            "mape": 6.4,
            "accuracy": 93.1,
        },
        "lstm": {
            "mae": 13.4,
            "rmse": 19.7,
            "mape": 6.9,
            "accuracy": 92.5,
        },
        "prophet": {
            "mae": 14.2,
            "rmse": 20.8,
            "mape": 7.3,
            "accuracy": 91.7,
        },
        "retrain": {
            "mae": 15.5,
            "rmse": 22.3,
            "mape": 8.5,
            "accuracy": 91.2,
        },
    }

    @staticmethod
    def start_training_job(model_type: str, csv_path: Optional[str] = None, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a training job row in DB and return its metadata. Actual
        training should be executed by a worker which updates this row.
        """
        db = SessionLocal()
        try:
            job = TrainingJob(model_type=model_type, status="queued", model_id=model_id, csv_path=csv_path)
            db.add(job)
            db.commit()
            db.refresh(job)
            return {
                "job_id": job.job_id,
                "model_type": job.model_type,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "metrics": job.metrics,
            }
        finally:
            db.close()

    @staticmethod
    def _metrics_for_model_type(model_type: str) -> Dict[str, Any]:
        return ForecastTrainingService.MODEL_TYPE_METRICS.get(
            model_type.lower(),
            ForecastTrainingService.MODEL_TYPE_METRICS["retrain"],
        ).copy()

    @staticmethod
    def get_training_job_status(job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a training job from DB"""
        db = SessionLocal()
        try:
            job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
            if not job:
                return None
            return {
                "job_id": job.job_id,
                "model_type": job.model_type,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "metrics": job.metrics,
            }
        finally:
            db.close()

    @staticmethod
    def complete_training_job(job_id: str, metrics: Dict) -> bool:
        """Mark a training job as complete and attach metrics"""
        db = SessionLocal()
        try:
            job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
            if not job:
                return False
            job.status = "completed"
            job.metrics = metrics
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            db.close()


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
        job = ForecastTrainingService.start_training_job("retrain", model_id=model_id)
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
        dbs = SessionLocal()
        try:
            models = dbs.query(ModelRegistry).all()
            for m in models:
                job = ForecastTrainingService.start_training_job(m.model_type, model_id=m.id)
                jobs.append({
                    "job_id": job["job_id"],
                    "model_id": m.id,
                    "model_type": m.model_type,
                })
        finally:
            dbs.close()

        return {
            "total_jobs": len(jobs),
            "jobs": jobs,
            "message": f"Retraining initiated for {len(jobs)} models",
        }

    @staticmethod
    def get_retraining_status(job_id: str) -> Optional[Dict[str, Any]]:
        """Get retraining job status"""
        return ForecastTrainingService.get_training_job_status(job_id)
