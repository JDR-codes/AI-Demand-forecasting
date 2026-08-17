# fastapi_app/schemas/validation_error_schema.py
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
    is_fixed: Optional[bool] = False
    is_ignored: Optional[bool] = False

    class Config:
        from_attributes = True


class ValidationErrorFixRequest(BaseModel):
    comments: Optional[str] = None


class ValidationErrorIgnoreRequest(BaseModel):
    reason: Optional[str] = None


class ValidationErrorBatchFixRequest(BaseModel):
    source: Optional[str] = None
    reason: Optional[str] = None
    severity: Optional[str] = None
    error_type: Optional[str] = None


class AutoFixResult(BaseModel):
    total: int
    fixed: int
    remaining: int
    message: str