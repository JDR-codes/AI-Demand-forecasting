from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ============= Forecast Schemas =============

class ForecastBase(BaseModel):
    model_id: Optional[str] = None
    sku: str
    region: str
    warehouse: str
    horizon: int
    predicted_demand: float
    confidence_score: Optional[float] = None
    model_used: str


class ForecastCreate(ForecastBase):
    pass


class ForecastUpdate(BaseModel):
    predicted_demand: Optional[float] = None
    confidence_score: Optional[float] = None
    status: Optional[str] = None


class ForecastResponse(ForecastBase):
    id: int
    forecast_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Training Schemas =============

class TrainingJobRequest(BaseModel):
    model_type: str  # arima, xgboost, lstm, prophet
    csv_path: Optional[str] = None
    steps: int = 7
    order: Optional[tuple] = (1, 1, 1)  # For ARIMA


class TrainingJobResponse(BaseModel):
    job_id: str
    model_type: str
    status: str
    created_at: datetime
    metrics: Optional[dict] = None

    class Config:
        from_attributes = True


# ============= Forecast Generation Schemas =============

class GenerateForecastRequest(BaseModel):
    model_id: str
    horizon: int
    sku: str
    region: str
    warehouse: str


class ForecastResultsResponse(BaseModel):
    id: int
    sku: str
    region: str
    warehouse: str
    predicted_demand: float
    confidence_score: Optional[float]
    model_used: str
    forecast_date: datetime

    class Config:
        from_attributes = True


# ============= Metrics Schemas =============

class MetricsResponse(BaseModel):
    model_type: str
    total_forecasts: int
    average_confidence: float
    accuracy_score: Optional[float]
    mae: Optional[float]
    rmse: Optional[float]
    mape: Optional[float]


# ============= Model Registry Schemas =============

class ModelRegistryCreate(BaseModel):
    name: str
    model_type: str
    version: str
    status: str = "active"


class ModelRegistryResponse(BaseModel):
    id: int
    name: str
    model_type: str
    version: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
