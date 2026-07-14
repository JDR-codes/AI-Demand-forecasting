# fastapi_app/schemas/data_source_dashboard_schema.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class DataSourceDashboardMetrics(BaseModel):
    """Dashboard metrics for data sources"""
    total_records: int
    active_connections: int
    total_connections: int
    sync_frequency: str
    validation_errors: int
    timestamp: datetime = datetime.utcnow()