from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TrainingConfigBase(BaseModel):
    model_registry_id: Optional[str] = None
    frequency: str = "daily"
    cron_expression: Optional[str] = None
    accuracy_threshold: float = 0.85
    minimum_records: int = 100
    validation_split: float = 0.2
    epochs: int = 20
    batch_size: int = 16
    learning_rate: float = 0.001
    enabled: bool = True


class TrainingConfigCreate(TrainingConfigBase):
    pass


class TrainingConfigUpdate(BaseModel):
    frequency: Optional[str] = None
    cron_expression: Optional[str] = None
    accuracy_threshold: Optional[float] = None
    minimum_records: Optional[int] = None
    validation_split: Optional[float] = None
    epochs: Optional[int] = None
    batch_size: Optional[int] = None
    learning_rate: Optional[float] = None
    enabled: Optional[bool] = None


class TrainingConfigResponse(TrainingConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True