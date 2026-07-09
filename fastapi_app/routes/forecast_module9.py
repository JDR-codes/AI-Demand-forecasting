from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from fastapi_app.db.session import get_db
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import (
    ForecastCreate,
    ForecastResponse,
    ForecastUpdate,
    TrainingJobRequest,
    TrainingJobResponse,
    GenerateForecastRequest,
    MetricsResponse,
    ModelRegistryCreate,
    ModelRegistryResponse,
)
from fastapi_app.services.forecast.forecast_db_service import (
    ForecastModelService,
    ForecastTrainingService,
    ForecastGenerationService,
    ForecastMetricsService,
    ForecastRetrainingService,
)
from fastapi_app.services.forecast.forecast_service import auto_forecast_report

router = APIRouter(prefix="/api/forecast", tags=["Forecast Engine"])


# ============= MODEL ENDPOINTS =============

@router.get("/models", response_model=List[dict])
def get_models(current_user: User = Depends(get_current_user)):
    """Get all registered forecast models - Tab: Model"""
    return ForecastModelService.get_all_models()


@router.post("/models", response_model=dict)
def create_model(
    model: ModelRegistryCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new forecast model - Tab: Model"""
    return ForecastModelService.create_model(
        name=model.name,
        model_type=model.model_type,
        version=model.version,
    )


@router.put("/models/{model_id}", response_model=dict)
def update_model(
    model_id: str,
    model_update: ModelRegistryCreate,
    current_user: User = Depends(get_current_user),
):
    """Update an existing forecast model - Tab: Model"""
    updated = ForecastModelService.update_model(model_id, **model_update.dict())
    if not updated:
        raise HTTPException(status_code=404, detail="Model not found")
    return updated


@router.delete("/models/{model_id}")
def delete_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a forecast model - Tab: Model"""
    success = ForecastModelService.delete_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}


# ============= TRAINING ENDPOINTS =============

@router.post("/train", response_model=TrainingJobResponse)
def train_model(
    training_request: TrainingJobRequest,
    current_user: User = Depends(get_current_user),
):
    """Start a training job - Tab: Run"""
    job = ForecastTrainingService.start_training_job(
        model_type=training_request.model_type,
        csv_path=training_request.csv_path,
    )
    return job


@router.get("/train/{job_id}", response_model=Optional[dict])
def get_training_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get training job status - Tab: Run"""
    job = ForecastTrainingService.get_training_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job


# ============= FORECAST GENERATION ENDPOINTS =============

@router.post("/generate", response_model=List[ForecastResponse])
def generate_forecast(
    forecast_request: GenerateForecastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new forecast - Tab: Forecast

    If `csv_path` is provided in the request body, run the forecasting
    pipeline immediately on that CSV and persist the resulting forecasts
    (one per model). Returns the persisted forecast rows.
    """
    # Require csv_path to run immediate processing
    if not forecast_request.csv_path:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide `csv_path` in the request to run immediate processing, "
                "or upload a CSV to media/uploads/csv for real-time processing."
            ),
        )

    # Run the auto report
    try:
        report = auto_forecast_report(path=forecast_request.csv_path, forecast_steps=forecast_request.horizon)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(exc)}")

    models_to_persist = {}
    for m in ("arima", "xgboost", "lstm", "prophet"):
        if m in report:
            models_to_persist[m] = report[m]

    if not models_to_persist and "model" in report:
        models_to_persist[report.get("requested_model", "auto")] = report["model"]

    persisted = []
    for model_name, model_report in models_to_persist.items():
        predicted = 0.0
        try:
            if isinstance(model_report, dict) and "forecast" in model_report:
                f = model_report["forecast"]
            elif isinstance(model_report, dict) and "future_predictions" in model_report:
                f = model_report["future_predictions"]
            else:
                f = model_report

            if hasattr(f, "__len__") and len(f) > 0:
                predicted = float(f[0])
            else:
                predicted = float(f)
        except Exception:
            predicted = 0.0

        forecast_data = ForecastCreate(
            model_id=forecast_request.model_id if forecast_request.model_id else None,
            sku=forecast_request.sku,
            region=forecast_request.region,
            warehouse=forecast_request.warehouse,
            horizon=forecast_request.horizon,
            predicted_demand=predicted,
            confidence_score=0.8,
            model_used=model_name,
        )

        created = ForecastGenerationService.generate_forecast(db, forecast_data)
        persisted.append(created)

    return persisted


@router.get("/results", response_model=List[ForecastResponse])
def get_forecast_results(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all forecast results - Tab: Forecast"""
    forecasts = ForecastGenerationService.get_forecast_results(db, limit=limit, offset=skip)
    return forecasts


@router.get("/results/{forecast_id}", response_model=ForecastResponse)
def get_forecast_by_id(
    forecast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific forecast result - Tab: Forecast"""
    forecast = ForecastGenerationService.get_forecast_by_id(db, forecast_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return forecast


# ============= METRICS ENDPOINTS =============

@router.get("/metrics", response_model=dict)
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get forecast metrics and performance statistics - Tab: Metrics"""
    metrics = ForecastMetricsService.get_metrics(db)
    return metrics


@router.get("/metrics/{model_type}", response_model=dict)
def get_model_metrics(
    model_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metrics for a specific model - Tab: Metrics"""
    metrics = ForecastMetricsService.get_model_metrics(db, model_type)
    return metrics


# ============= RETRAINING ENDPOINTS =============

@router.post("/retrain", response_model=dict)
def retrain_model(
    model_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrain a specific model - Tab: Retraining"""
    result = ForecastRetrainingService.retrain_model(db, model_id)
    return result


@router.post("/retrain-all", response_model=dict)
def retrain_all_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrain all registered models - Tab: Retraining"""
    result = ForecastRetrainingService.retrain_all_models(db)
    return result


@router.get("/retrain/{job_id}", response_model=dict)
def get_retrain_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get retraining job status - Tab: Retraining"""
    status = ForecastRetrainingService.get_retraining_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Retraining job not found")
    return status
