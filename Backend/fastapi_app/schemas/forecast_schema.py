# fastapi_app/schemas/forecast_schema.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ForecastJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============= Forecast Job Schemas =============

class ForecastJobCreate(BaseModel):
    upload_id: Optional[int] = None
    processing_job_id: Optional[str] = None
    model_registry_id: Optional[str] = None
    forecast_horizon: int = 7
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict)
    sku: Optional[str] = "default"
    region: Optional[str] = None
    warehouse: Optional[str] = None


class ForecastJobResponse(BaseModel):
    id: int
    job_id: str
    upload_id: Optional[int]
    processing_job_id: Optional[str]
    model_registry_id: Optional[str]
    status: ForecastJobStatus
    progress_percentage: float
    current_step: int
    current_step_name: Optional[str]
    current_step_message: Optional[str]
    failed_step: Optional[int]
    failed_step_name: Optional[str]
    forecast_horizon: int
    sku: Optional[str]
    region: Optional[str]
    warehouse: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    elapsed_time: Optional[float]
    remaining_seconds: Optional[float]
    forecast_start_date: Optional[datetime]
    forecast_end_date: Optional[datetime]
    metrics: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ForecastJobStepResponse(BaseModel):
    id: int
    step_number: int
    step_name: str
    status: str
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    message: Optional[str]
    
    class Config:
        from_attributes = True


# ============= Forecast Result Schemas =============

class ForecastResultResponse(BaseModel):
    id: int
    forecast_job_id: int
    sku: str
    region: Optional[str]
    warehouse: Optional[str]
    forecast_date: datetime
    prediction: float
    actual_value: Optional[float]
    confidence_upper: Optional[float]
    confidence_lower: Optional[float]
    confidence_score: Optional[float]
    is_peak: bool
    is_forecast: bool
    model_used: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ForecastChartData(BaseModel):
    historical: List[float]
    forecast: List[float]
    upper: List[float]
    lower: List[float]
    labels: List[str]
    split_index: int
    total_points: int
    peak_days: List[Dict[str, Any]]
    forecast_start: Optional[str]
    
    class Config:
        from_attributes = True


class ForecastSummary(BaseModel):
    forecasted_demand: float
    avg_daily_demand: float
    peak_day: int
    peak_value: float
    expected_revenue: float
    inventory_risk: str
    accuracy: float
    total_points: int
    confidence_level: float
    unit_price_used: float = 30.0
    
    class Config:
        from_attributes = True


# ============= Training Job Schemas =============

class TrainingJobCreate(BaseModel):
    model_type: str
    model_registry_id: Optional[str] = None
    upload_id: Optional[int] = None
    processing_job_id: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict)
    epochs: Optional[int] = 20
    batch_size: Optional[int] = 16
    learning_rate: Optional[float] = 0.001


class TrainingJobResponse(BaseModel):
    job_id: str
    model_registry_id: Optional[str]
    upload_id: Optional[int]
    processing_job_id: Optional[str]
    model_type: str
    status: str
    progress_percentage: float
    current_epoch: int
    total_epochs: Optional[int]
    current_step: Optional[str]
    current_step_name: Optional[str]
    current_step_message: Optional[str]
    failed_step: Optional[int]
    failed_step_name: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    elapsed_time: Optional[float]
    remaining_time: Optional[float]
    metrics: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TrainingStepResponse(BaseModel):
    id: int
    step_number: int
    step_name: str
    status: str
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    message: Optional[str]
    
    class Config:
        from_attributes = True


class TrainingHistoryResponse(BaseModel):
    id: int
    version: str
    accuracy_before: Optional[float]
    accuracy_after: Optional[float]
    improvement_percentage: Optional[float]
    rmse_before: Optional[float]
    rmse_after: Optional[float]
    mae_before: Optional[float]
    mae_after: Optional[float]
    mape_before: Optional[float]
    mape_after: Optional[float]
    duration_seconds: Optional[float]
    epochs: Optional[int]
    dataset_size: Optional[int]
    status: str
    trained_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    notes: Optional[str]
    metrics: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


# ============= Model Registry Schemas =============

class ModelRegistryCreate(BaseModel):
    name: str
    model_type: str
    version: str = "1.0.0"
    description: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_default: bool = False


class ModelRegistryResponse(BaseModel):
    id: str
    name: str
    model_type: str
    version: str
    is_default: bool
    is_active: bool
    is_favorite: bool = False
    deployment_status: str = "development"
    last_trained: Optional[datetime]
    training_size: Optional[int]
    best_accuracy: Optional[float]
    best_rmse: Optional[float]
    best_mae: Optional[float]
    best_mape: Optional[float]
    best_r2: Optional[float]
    best_loss: Optional[float]
    framework: Optional[str]
    algorithm: Optional[str]
    hyperparameters: Optional[Dict[str, Any]]
    feature_set: Optional[List[str]]
    artifact_path: Optional[str]
    artifact_size: Optional[int]
    training_duration: Optional[float]
    framework_version: Optional[str]
    status: str
    description: Optional[str]
    archived_at: Optional[datetime]
    production_version: Optional[str]
    production_deployed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Model Config Schemas =============

class ModelConfigResponse(BaseModel):
    id: str
    name: str
    model_type: str
    forecast_horizon: int
    seasonality: bool
    validation_split: float
    default_dataset: Optional[str]
    default_region: Optional[str]
    default_sku: Optional[str]
    default_warehouse: Optional[str]
    epochs: Optional[int]
    batch_size: Optional[int]
    learning_rate: Optional[float]
    is_default: bool
    last_trained: Optional[str]
    accuracy: Optional[float]
    dataset_size: Optional[int]
    date_range: Optional[Dict[str, str]]
    last_updated: Optional[str]
    
    class Config:
        from_attributes = True


class ModelConfigUpdate(BaseModel):
    forecast_horizon: Optional[int] = None
    seasonality: Optional[bool] = None
    validation_split: Optional[float] = None
    default_dataset: Optional[str] = None
    default_region: Optional[str] = None
    default_sku: Optional[str] = None
    default_warehouse: Optional[str] = None
    epochs: Optional[int] = None
    batch_size: Optional[int] = None
    learning_rate: Optional[float] = None


# ============= Dashboard Schemas =============

class ForecastDashboardSummary(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    queued_jobs: int
    total_forecasts: int
    active_models: int
    total_models: int
    average_accuracy: Optional[float]
    average_rmse: Optional[float]
    average_mae: Optional[float]
    average_mape: Optional[float]
    latest_training: Optional[datetime]
    best_model: Optional[Dict[str, Any]]
    recent_jobs: Optional[List[Dict[str, Any]]] = []
    training_jobs: Optional[List[Dict[str, Any]]] = []
    timestamp: Optional[str] = None


class ForecastMetricsHistory(BaseModel):
    date: str
    accuracy: float
    rmse: float
    mae: float
    mape: float
    r2: float


class ForecastMetricsComparison(BaseModel):
    name: str
    accuracy: float
    rmse: float
    mae: float
    mape: float
    r2: float


class DatasetOptionResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    record_count: Optional[int]
    category: Optional[str]

    class Config:
        from_attributes = True


class DatasetDimensionResponse(BaseModel):
    categories: List[str]
    regions: List[str]
    warehouses: List[str]
    skus: List[str]


class PaginatedForecastTableResponse(BaseModel):
    results: List[ForecastResultResponse]
    total: int
    limit: int
    offset: int


# ============= Retraining Configuration Schemas =============

class TrainingConfigurationResponse(BaseModel):
    id: int
    model_registry_id: Optional[str]
    forecast_horizon: int
    seasonality: bool
    validation_split: float
    epochs: int
    batch_size: int
    learning_rate: float
    default_dataset: Optional[str]
    default_region: Optional[str]
    default_sku: Optional[str]
    default_warehouse: Optional[str]
    frequency: str
    cron_expression: Optional[str]
    accuracy_threshold: float
    minimum_records: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingConfigurationUpdate(BaseModel):
    forecast_horizon: Optional[int] = None
    seasonality: Optional[bool] = None
    validation_split: Optional[float] = None
    epochs: Optional[int] = None
    batch_size: Optional[int] = None
    learning_rate: Optional[float] = None
    default_dataset: Optional[str] = None
    default_region: Optional[str] = None
    default_sku: Optional[str] = None
    default_warehouse: Optional[str] = None
    frequency: Optional[str] = None
    cron_expression: Optional[str] = None
    accuracy_threshold: Optional[float] = None
    minimum_records: Optional[int] = None
    enabled: Optional[bool] = None


class RetrainingScheduleResponse(BaseModel):
    scheduled_run: datetime
    model_registry_id: str
    model_name: str
    model_type: str
    accuracy_threshold: float
    status: str

    class Config:
        from_attributes = True


class OneShotScheduleRequest(BaseModel):
    run_at: datetime