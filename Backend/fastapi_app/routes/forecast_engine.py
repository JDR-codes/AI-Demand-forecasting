# fastapi_app/routes/forecast_engine.py
from fastapi import APIRouter, Query, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import (
    ForecastDashboardSummary,
    ModelConfigResponse,
    ModelConfigUpdate,
    ForecastMetricsHistory,
    ForecastMetricsComparison
)
from fastapi_app.services.forecast.forecast_dashboard_service import ForecastDashboardService
from fastapi_app.services.forecast.forecast_metrics_dashboard_service import ForecastMetricsDashboardService
from fastapi_app.services.forecast.model_config_service import ModelConfigService
from fastapi_app.services.forecast.forecast_job_service import ForecastJobService

router = APIRouter(prefix="/api/forecast", tags=["Forecast"])


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard", response_model=ForecastDashboardSummary)
def forecast_dashboard(
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get forecast dashboard summary with metrics."""
    return ForecastDashboardService.get_summary(db, model_type)


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

@router.get("/models/{model_id}/config", response_model=ModelConfigResponse)
def get_model_config(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get model configuration for the Figma popup."""
    config = ModelConfigService.get_model_config(db, model_id)
    if not config:
        raise HTTPException(status_code=404, detail="Model not found")
    return config


@router.put("/models/{model_id}/config", response_model=ModelConfigResponse)
def update_model_config(
    model_id: str,
    update: ModelConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update model configuration."""
    config = ModelConfigService.update_model_config(db, model_id, update)
    if not config:
        raise HTTPException(status_code=404, detail="Model not found")
    return config


# ============================================================================
# METRICS
# ============================================================================

@router.get("/metrics/history")
def get_metrics_history(
    days: int = Query(30, ge=1, le=365),
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get historical metrics for chart."""
    return ForecastMetricsDashboardService.get_metrics_history(db, days, model_type)


@router.get("/metrics/comparison")
def get_metrics_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get comparison metrics across model types."""
    return ForecastMetricsDashboardService.get_metrics_comparison(db)


@router.get("/metrics/best")
def get_best_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[Dict[str, Any]]:
    """Get the best performing model."""
    return ForecastMetricsDashboardService.get_best_model(db)


# ============================================================================
# MODEL EXECUTION (Run individual models)
# ============================================================================

@router.post("/models/{model_id}/run")
def run_model(
    model_id: str,
    forecast_horizon: int = Query(7, ge=1, le=90),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Run a specific model directly."""
    from fastapi_app.models.model_registry_model import ModelRegistry
    from fastapi_app.services.background.task_manager import TaskManager
    
    # Verify model exists
    model = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not model.is_active:
        raise HTTPException(status_code=400, detail="Model is not active")
    
    # Create a forecast job with this model
    from fastapi_app.schemas.forecast_schema import ForecastJobCreate
    
    job_config = ForecastJobCreate(
        model_registry_id=model_id,
        forecast_horizon=forecast_horizon,
        sku="default"
    )
    
    job = ForecastJobService.create_job(db, job_config, current_user.id)
    
    # Start job in background
    TaskManager.run_forecast_job(job.job_id)
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "model_id": model_id,
        "model_name": model.name,
        "forecast_horizon": forecast_horizon,
        "message": f"Forecast job started for model {model.name}"
    }