# fastapi_app/routes/forecast_engine.py
from fastapi import APIRouter, Query, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from fastapi_app.core.dependencies import get_current_user, require_permission_dep
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import (
    ForecastDashboardSummary,
    ModelConfigResponse,
    ModelConfigUpdate,
    ForecastMetricsHistory,
    ForecastMetricsComparison,
    DatasetOptionResponse,
    DatasetDimensionResponse
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
    current_user: User = Depends(require_permission_dep("forecast:read")),
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
    current_user: User = Depends(require_permission_dep("forecast:read")),
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
    current_user: User = Depends(require_permission_dep("forecast:run")),
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
    current_user: User = Depends(require_permission_dep("forecast:read")),
) -> List[Dict[str, Any]]:
    """Get historical metrics for chart."""
    return ForecastMetricsDashboardService.get_metrics_history(db, days, model_type)


@router.get("/metrics/comparison")
def get_metrics_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read")),
) -> List[Dict[str, Any]]:
    """Get comparison metrics across model types."""
    return ForecastMetricsDashboardService.get_metrics_comparison(db)


@router.get("/metrics/best")
def get_best_model(
    sku: Optional[str] = Query(None, description="Filter by SKU to get best model per SKU"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read")),
) -> Optional[Dict[str, Any]]:
    """Get the best performing model (globally or filtered by SKU)."""
    return ForecastMetricsDashboardService.get_best_model(db, sku)


# ============================================================================
# MODEL EXECUTION (Run individual models)
# ============================================================================

@router.post("/models/{model_id}/run")
def run_model(
    model_id: str,
    forecast_horizon: int = Query(7, ge=1, le=90),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run")),
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


# ============================================================================
# DATASETS & DIMENSIONS
# ============================================================================

@router.get("/datasets", response_model=List[DatasetOptionResponse])
def get_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read")),
) -> List[Any]:
    """List completed processed datasets for selecting as forecast inputs."""
    from fastapi_app.models.processing_job_model import ProcessedDataset, ProcessingJob
    from sqlalchemy import desc
    
    query = db.query(ProcessedDataset).join(
        ProcessingJob, ProcessedDataset.processing_job_id == ProcessingJob.id
    ).filter(
        ProcessingJob.status == "completed"
    )
    
    # If the user is not admin, filter by job owner
    if current_user.role.name not in ["Admin", "Super Admin"]:
        query = query.filter(ProcessingJob.created_by == current_user.id)
        
    return query.order_by(desc(ProcessedDataset.created_at)).all()


@router.get("/datasets/{dataset_id}/dimensions", response_model=DatasetDimensionResponse)
def get_dataset_dimensions(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read")),
) -> Dict[str, List[str]]:
    """Extract distinct SKUs, Warehouses, Regions, and Categories from a processed dataset."""
    import os
    import pandas as pd
    from fastapi_app.models.processing_job_model import ProcessedDataset
    
    dataset = db.query(ProcessedDataset).filter(ProcessedDataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Processed dataset file not found")
        
    try:
        if dataset.file_path.endswith(".parquet"):
            import pyarrow.parquet as pq
            meta = pq.read_metadata(dataset.file_path)
            cols = meta.schema.names
            
            load_cols = [c for c in ["category", "region", "warehouse", "sku"] if c in cols]
            if not load_cols:
                return {"categories": [], "regions": [], "warehouses": [], "skus": []}
                
            df = pd.read_parquet(dataset.file_path, columns=load_cols)
        else:
            header_df = pd.read_csv(dataset.file_path, nrows=0)
            cols = header_df.columns.tolist()
            load_cols = [c for c in ["category", "region", "warehouse", "sku"] if c in cols]
            if not load_cols:
                return {"categories": [], "regions": [], "warehouses": [], "skus": []}
            df = pd.read_csv(dataset.file_path, usecols=load_cols)
            
        categories = sorted(df["category"].dropna().unique().tolist()) if "category" in df.columns else []
        regions = sorted(df["region"].dropna().unique().tolist()) if "region" in df.columns else []
        warehouses = sorted(df["warehouse"].dropna().unique().tolist()) if "warehouse" in df.columns else []
        skus = sorted(df["sku"].dropna().unique().tolist()) if "sku" in df.columns else []
        
        return {
            "categories": [str(x) for x in categories],
            "regions": [str(x) for x in regions],
            "warehouses": [str(x) for x in warehouses],
            "skus": [str(x) for x in skus]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset dimensions: {str(e)}")


@router.get("/preview")
def preview_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read")),
):
    """Preview basic stats of a dataset before running forecast."""
    import os
    from fastapi_app.models.processing_job_model import ProcessedDataset
    from fastapi_app.services.forecast.forecast_preview_service import ForecastPreviewService
    
    dataset = db.query(ProcessedDataset).filter(ProcessedDataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
        
    result = ForecastPreviewService.preview_dataset(dataset.file_path)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result