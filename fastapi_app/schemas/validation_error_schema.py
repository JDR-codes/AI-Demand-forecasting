from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ValidationErrorOut(BaseModel):
    id: int
    source: str
    error_type: str
    severity: str
    rows_affected: int
    status: str
    column_name: Optional[str] = None
    row_number: Optional[int] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    error_message: Optional[str] = None
    suggestion: Optional[str] = None
    fixed_reason: Optional[str] = None
    ignored_reason: Optional[str] = None
    fixed_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ValidationErrorFixRequest(BaseModel):
    fix_type: str  # "fix" or "ignore"
    comments: Optional[str] = None
    reason: Optional[str] = None  # For ignoring


class ValidationErrorBatchFixRequest(BaseModel):
    source: Optional[str] = None
    reason: Optional[str] = None
    severity: Optional[str] = None
    error_type: Optional[str] = None