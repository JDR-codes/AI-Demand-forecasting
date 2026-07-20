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
    health_percentage: float = 0.0
    today_syncs: int = 0
    today_failed_syncs: int = 0
    today_successful_syncs: int = 0
    recent_uploads: int = 0
    recent_validations: int = 0
    timestamp: datetime = datetime.utcnow()


class DashboardTrendPoint(BaseModel):
    """Single point in dashboard trend"""
    date: str
    syncs: int
    uploads: int
    errors: int
    successful_syncs: int
    failed_syncs: int


class DashboardTrendResponse(BaseModel):
    """Dashboard trend response"""
    trends: List[DashboardTrendPoint]
    total_syncs: int
    total_uploads: int
    total_errors: int
    success_rate: float
    timestamp: datetime = datetime.utcnow()