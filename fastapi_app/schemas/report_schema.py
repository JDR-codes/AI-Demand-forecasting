from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    title: Optional[str] = None
    report_type: str = Field(
        ...,
        description=(
            "One of: forecast_summary | inventory_health | "
            "recommendation_summary | scenario_comparison | full_system"
        ),
    )
    format: Optional[str] = Field(default="json", description="json or csv")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional filters. E.g. {\"sku\": \"SKU-001\", \"warehouse\": \"WH-A\", "
            "\"limit\": 50}"
        ),
    )


class ReportResponse(BaseModel):
    id: int
    title: str
    report_type: str
    status: str
    format: str
    parameters: Optional[Dict[str, Any]] = None
    data: Optional[Any] = None
    summary: Optional[str] = None
    generated_by: Optional[int] = None
    generated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    id: int
    title: str
    report_type: str
    status: str
    format: str
    generated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
