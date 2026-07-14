from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    report_type: str = Field(
        ...,
        description=(
            "One of: executive_summary | demand_summary | forecast_summary | "
            "model_performance | inventory_health | stockout_risk | "
            "recommendation_summary | scenario_comparison | full_system | "
            "custom_report"
        ),
    )
    format: Optional[str] = Field(default="json", description="json, csv, pdf, or excel")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional filters. E.g. {\"sku\": \"SKU-001\", \"region\": \"West\", "
            "\"category\": \"Electronics\", \"date_range\": \"last_30_days\", "
            "\"limit\": 50}"
        ),
    )


class ReportResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    report_type: str
    status: str
    format: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
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
    description: Optional[str] = None
    report_type: str
    status: str
    format: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    generated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SKUPerformanceResponse(BaseModel):
    sku: str
    product: str
    revenue: float
    units_sold: int
    forecast_accuracy: float
    yoy_change: float


class SKUDetailsResponse(BaseModel):
    sku: str
    product: str
    revenue: float
    units_sold: int
    forecast_accuracy: float
    yoy_change: float
    demand_forecast_12m: List[Dict[str, Any]]
    accuracy_trend_12m: List[Dict[str, Any]]
    sales_by_region: Dict[str, Any]
    stock_by_warehouse: Dict[str, Any]
    monthly_performance: List[Dict[str, Any]]
