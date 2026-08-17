#fastapi_app/schemas/model_config_schema.py

from pydantic import BaseModel
from typing import Optional


class ModelConfigUpdate(BaseModel):
    """Update model configuration."""
    forecast_horizon: Optional[int] = None
    seasonality: Optional[bool] = None
    validation_split: Optional[float] = None
    default_dataset: Optional[str] = None
    default_region: Optional[str] = None
    default_sku: Optional[str] = None
    epochs: Optional[int] = None
    batch_size: Optional[int] = None
    learning_rate: Optional[float] = None
    is_default: Optional[bool] = None


class ModelConfigResponse(BaseModel):
    """Model configuration response."""
    id: str
    name: str
    model_type: str
    forecast_horizon: int
    seasonality: bool
    validation_split: float
    default_dataset: Optional[str]
    default_region: Optional[str]
    default_sku: Optional[str]
    epochs: Optional[int]
    batch_size: Optional[int]
    learning_rate: Optional[float]
    is_default: bool
    last_trained: Optional[str]
    accuracy: Optional[float]