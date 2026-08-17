# fastapi_app/schemas/processing_input_schema.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProcessingJobInputResponse(BaseModel):
    id: int
    processing_job_id: int
    input_type: str
    data_source_id: Optional[int] = None
    upload_id: Optional[int] = None
    category: str
    status: str
    records_loaded: int
    records_processed: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
