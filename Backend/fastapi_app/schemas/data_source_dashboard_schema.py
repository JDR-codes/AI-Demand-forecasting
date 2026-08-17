# fastapi_app/schemas/data_source_dashboard_schema.py
from pydantic import BaseModel
from typing import Dict, Any, Optional


class DataSourceDashboardMetrics(BaseModel):
    total_records: int
    active_connections: int
    total_connections: int
    sync_frequency: str
    validation_errors: int
    health_status: Optional[Dict[str, int]] = None  # healthy, warning, error counts

    class Config:
        from_attributes = True