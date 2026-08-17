#fastapi_app/schemas/processing_schema.py
from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from fastapi_app.schemas.processing_input_schema import ProcessingJobInputResponse


class ProcessingJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJobCreate(BaseModel):
    data_source_ids: List[int] = []
    upload_ids: List[int] = []
    category_mode: Literal["selected", "all"] = "selected"
    categories: List[str] = []
    merge_strategy: Literal["append", "separate"] = "separate"
    deduplicate: bool = True
    run_validation: bool = True
    run_outlier_detection: bool = True
    run_feature_engineering: bool = True

    @model_validator(mode="after")
    def validate_selection(self):
        if not self.data_source_ids and not self.upload_ids:
            raise ValueError("Select at least one data source or upload")
        if self.category_mode == "selected" and not self.categories:
            raise ValueError("Select at least one category")
        return self


class ProcessingJobResponse(BaseModel):
    id: int
    job_id: str
    upload_id: Optional[int] = None
    dataset_path: Optional[str] = None
    datasource_id: Optional[int] = None
    category_mode: str
    categories: List[str]
    merge_strategy: str
    deduplicate: bool
    run_validation: bool
    run_outlier_detection: bool
    run_feature_engineering: bool
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
    warning_message: Optional[str] = None
    created_at: datetime
    inputs: List[ProcessingJobInputResponse] = []

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