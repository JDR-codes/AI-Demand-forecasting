# fastapi_app/schemas/upload_schema.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class UploadOut(BaseModel):
    id: int
    filename: str
    unique_filename: str
    file_path: str
    file_url: str
    status: str
    uploaded_by: Optional[int] = None
    uploaded_at: datetime
    file_size: Optional[int] = None
    rows: Optional[int] = None
    columns: Optional[int] = None
    processing_progress: Optional[float] = 0.0
    processing_status: Optional[str] = "pending"
    duration_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class UploadPreviewRow(BaseModel):
    """Single row in upload preview."""
    class Config:
        arbitrary_types_allowed = True


class UploadPreviewOut(BaseModel):
    """Upload preview response."""
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    upload_id: int
    filename: str

    class Config:
        from_attributes = True


class UploadStatsOut(BaseModel):
    """Upload statistics response."""
    total: int
    pending: int
    processed: int
    failed: int
    total_size_bytes: int
    total_size_mb: float

    class Config:
        from_attributes = True