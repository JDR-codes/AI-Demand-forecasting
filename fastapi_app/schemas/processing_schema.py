#fastapi_app/schemas/processing_schema.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ProcessingJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJobCreate(BaseModel):
    upload_id: Optional[int] = None
    dataset_path: Optional[str] = None


class ProcessingJobResponse(BaseModel):
    id: int
    job_id: str
    upload_id: Optional[int]
    dataset_path: Optional[str]
    status: ProcessingJobStatus
    progress_percentage: float
    current_step: str
    records_loaded: int
    records_processed: int
    records_failed: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    paused_at: Optional[datetime]
    duration_seconds: Optional[float]
    eta_seconds: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProcessingStepResponse(BaseModel):
    id: int
    step_number: int
    step_name: str
    status: str
    progress: float
    records_processed: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    message: Optional[str]
    
    class Config:
        from_attributes = True


class ProcessingLogResponse(BaseModel):
    timestamp: datetime
    level: str
    message: str
    step: Optional[str]
    
    class Config:
        from_attributes = True


class ProcessingOutlierResponse(BaseModel):
    column: str
    method: str
    total_outliers: int
    removed: int
    capped: int
    normal_values: int
    percentage_removed: float
    percentage_capped: float
    spike_rows: List[int]
    
    class Config:
        from_attributes = True


class ProcessingFeatureResponse(BaseModel):
    name: str
    type: str
    description: Optional[str]
    importance: Optional[float]
    
    class Config:
        from_attributes = True


class ProcessingHistoryResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    records_loaded: int
    records_processed: int
    duration_seconds: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    dataset: Optional[str]
    created_by: Optional[str]
    
    class Config:
        from_attributes = True