from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class SummaryMetrics(BaseModel):
    total_skus: int
    total_warehouses: int
    total_forecasts: int
    total_recommendations: int
    critical_alerts: int
    health_score: float


class DashboardSummary(BaseModel):
    metrics: SummaryMetrics
    timestamp: datetime


class DemandTrendPoint(BaseModel):
    date: str
    demand: float
    forecast: float
    variance: float


class DemandTrend(BaseModel):
    trend: List[DemandTrendPoint]
    avg_demand: float
    peak_demand: float
    min_demand: float
    forecast_accuracy: float


class RegionalForecast(BaseModel):
    region: str
    sku: str
    forecasted_demand: float
    confidence: float
    trend: str


class RegionalForecastData(BaseModel):
    forecasts: List[RegionalForecast]
    total_regions: int
    timestamp: datetime


class WarehouseInventory(BaseModel):
    warehouse_id: str
    sku: str
    current_stock: float
    safety_stock: float
    reorder_point: float
    status: str


class WarehouseDistribution(BaseModel):
    inventory: List[WarehouseInventory]
    total_warehouses: int
    total_stock_value: float
    timestamp: datetime


class AIInsight(BaseModel):
    title: str
    description: str
    impact: str
    recommendation: str
    priority: str


class AIInsights(BaseModel):
    insights: List[AIInsight]
    generated_at: datetime


class Alert(BaseModel):
    alert_id: int
    title: str
    severity: str
    category: str
    message: str
    created_at: datetime
    is_read: bool


class LiveAlerts(BaseModel):
    alerts: List[Alert]
    critical_count: int
    warning_count: int
    info_count: int
    total_count: int


class TopSKU(BaseModel):
    sku: str
    name: str
    total_demand: float
    forecast_demand: float
    current_stock: float
    turnover_rate: float
    revenue_impact: str


class TopSKUs(BaseModel):
    top_skus: List[TopSKU]
    timestamp: datetime
