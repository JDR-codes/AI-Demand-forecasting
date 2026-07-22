# fastapi_app/schemas/scenario_schema.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ScenarioStatus(str, Enum):
    DRAFT = "draft"
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# BULK DELETE
# ============================================================================

class BulkDeleteRequest(BaseModel):
    scenario_ids: List[int]


# ============================================================================
# SCENARIO BASE
# ============================================================================

class ScenarioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    time_horizon: int = Field(30, ge=1, le=365)
    region: Optional[str] = Field(None, max_length=100)
    warehouse: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    sku: Optional[str] = Field(None, max_length=100)
    demand_surge: float = Field(0.0, ge=-50, le=100)
    discount: float = Field(0.0, ge=0, le=100)
    price_change: float = Field(0.0, ge=-50, le=50)
    supply_delay: int = Field(0, ge=0, le=30)
    seasonal_impact: float = Field(0.0, ge=-50, le=50)
    forecast_model: str = Field("arima", pattern="^(arima|xgboost|lstm|prophet|auto)$")
    parameters: Optional[Dict[str, Any]] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    @field_validator('demand_surge')
    @classmethod
    def validate_demand_surge(cls, v: float) -> float:
        if v < -50 or v > 100:
            raise ValueError('Demand surge must be between -50 and 100')
        return v

    @field_validator('discount')
    @classmethod
    def validate_discount(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError('Discount must be between 0 and 100')
        return v

    @field_validator('price_change')
    @classmethod
    def validate_price_change(cls, v: float) -> float:
        if v < -50 or v > 50:
            raise ValueError('Price change must be between -50 and 50')
        return v

    @field_validator('supply_delay')
    @classmethod
    def validate_supply_delay(cls, v: int) -> int:
        if v < 0 or v > 30:
            raise ValueError('Supply delay must be between 0 and 30')
        return v

    @field_validator('seasonal_impact')
    @classmethod
    def validate_seasonal_impact(cls, v: float) -> float:
        if v < -50 or v > 50:
            raise ValueError('Seasonal impact must be between -50 and 50')
        return v


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    time_horizon: Optional[int] = Field(None, ge=1, le=365)
    region: Optional[str] = Field(None, max_length=100)
    warehouse: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    sku: Optional[str] = Field(None, max_length=100)
    demand_surge: Optional[float] = Field(None, ge=-50, le=100)
    discount: Optional[float] = Field(None, ge=0, le=100)
    price_change: Optional[float] = Field(None, ge=-50, le=50)
    supply_delay: Optional[int] = Field(None, ge=0, le=30)
    seasonal_impact: Optional[float] = Field(None, ge=-50, le=50)
    forecast_model: Optional[str] = Field(None, pattern="^(arima|xgboost|lstm|prophet|auto)$")
    status: Optional[ScenarioStatus] = None
    parameters: Optional[Dict[str, Any]] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip() if v else v


class ScenarioResponse(ScenarioBase):
    id: int
    status: ScenarioStatus
    progress: float
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    executed_by: Optional[int] = None
    deleted_by: Optional[int] = None
    exported_by: Optional[int] = None
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_output: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    exported_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# SCENARIO RUN
# ============================================================================

class ScenarioRunResponse(BaseModel):
    id: int
    run_id: str
    scenario_id: int
    status: str
    progress: float
    current_step: Optional[str] = None
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    logs: Optional[List[Dict[str, Any]]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScenarioProgressResponse(BaseModel):
    run_id: str
    status: str
    progress: float
    current_step: Optional[str] = None
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    duration_seconds: Optional[float] = None


# ============================================================================
# SCENARIO METRICS
# ============================================================================

class ScenarioMetricsResponse(BaseModel):
    demand_impact: Optional[float] = None
    inventory_impact: Optional[float] = None
    revenue_impact: Optional[float] = None
    stockout_risk: Optional[float] = None
    total_demand: Optional[float] = None
    total_inventory: Optional[float] = None
    total_revenue: Optional[float] = None
    stockout_count: Optional[int] = 0


class ScenarioSummaryResponse(BaseModel):
    scenario_id: int
    name: str
    status: str
    metrics: ScenarioMetricsResponse
    created_at: datetime


# ============================================================================
# SCENARIO CHARTS
# ============================================================================

class ScenarioChartResponse(BaseModel):
    labels: List[str]
    baseline: List[float]
    simulation: List[float]
    difference: Optional[List[float]] = None
    title: Optional[str] = None


class ComparisonChartResponse(BaseModel):
    labels: List[str]
    baseline: List[float]
    scenarios: Dict[str, List[float]]
    best_scenario: Optional[str] = None


# ============================================================================
# STOCKOUT SKUS
# ============================================================================

class StockoutSKUResponse(BaseModel):
    sku: str
    product_name: Optional[str] = None
    demand: float
    shortage: float
    revenue_risk: float
    risk_level: str  # high, medium, low
    current_stock: Optional[float] = None
    recommended_quantity: Optional[float] = None
    lost_sales: Optional[float] = None


# ============================================================================
# ALL SKUS
# ============================================================================

class AllSKUResponse(BaseModel):
    sku: str
    product_name: Optional[str] = None
    forecast: float
    inventory: float
    demand_percentage: float
    inventory_percentage: float
    stockout_risk: Optional[float] = None


# ============================================================================
# COMPARISON
# ============================================================================

class ScenarioComparisonRequest(BaseModel):
    scenario_ids: List[int] = Field(..., min_length=2, max_length=10)


class ScenarioComparisonResponse(BaseModel):
    comparison_id: str
    scenarios: List[ScenarioResponse]
    best_scenario_id: Optional[int] = None
    comparison_summary: Dict[str, Any]
    comparison_chart: Optional[Dict[str, Any]] = None
    created_at: datetime


# ============================================================================
# SCENARIO CARDS
# ============================================================================

class ScenarioCardResponse(BaseModel):
    highest_demand: Optional[ScenarioResponse] = None
    lowest_inventory: Optional[ScenarioResponse] = None
    lowest_risk: Optional[ScenarioResponse] = None
    highest_revenue: Optional[ScenarioResponse] = None


# ============================================================================
# SCENARIO TABLE
# ============================================================================

class ScenarioTableRow(BaseModel):
    id: int
    name: str
    demand_impact: Optional[float] = None
    inventory_impact: Optional[float] = None
    revenue_impact: Optional[float] = None
    stockout_risk: Optional[float] = None
    status: str
    created_at: datetime
    actions: List[str] = ["view", "run", "delete", "export"]


class ScenarioTableResponse(BaseModel):
    total: int
    page: int
    pages: int
    items: List[ScenarioTableRow]


# ============================================================================
# PARAMETER ADJUSTMENT
# ============================================================================

class ScenarioParameterAdjustment(BaseModel):
    demand_surge: Optional[float] = Field(None, ge=-50, le=100)
    discount: Optional[float] = Field(None, ge=0, le=100)
    price_change: Optional[float] = Field(None, ge=-50, le=50)
    supply_delay: Optional[int] = Field(None, ge=0, le=30)
    seasonal_impact: Optional[float] = Field(None, ge=-50, le=50)


# ============================================================================
# FILTER
# ============================================================================

class ScenarioFilter(BaseModel):
    search: Optional[str] = None
    status: Optional[str] = None
    region: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    forecast_model: Optional[str] = None
    created_by: Optional[int] = None
    last_run_status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sort: Optional[str] = "-created_at"


# ============================================================================
# EXPORT
# ============================================================================

class ScenarioExportResponse(BaseModel):
    message: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    format: str


# ============================================================================
# DASHBOARD CARDS
# ============================================================================

class ScenarioDashboardCardsResponse(BaseModel):
    total_scenarios: int
    completed: int
    running: int
    failed: int
    cancelled: int
    today_simulations: int
    average_revenue: float
    average_demand: float
    average_risk: float


# ============================================================================
# DASHBOARD ANALYTICS
# ============================================================================

class ScenarioDashboardAnalyticsResponse(BaseModel):
    total_scenarios: int
    completed: int
    running: int
    failed: int
    cancelled: int
    today_simulations: int
    week_simulations: int
    month_simulations: int
    average_revenue: float
    average_demand: float
    average_inventory: float
    average_risk: float
    average_run_time: float
    success_rate: float
    top_performing_scenario: Optional[Dict[str, Any]] = None
    highest_revenue_scenario: Optional[Dict[str, Any]] = None
    lowest_risk_scenario: Optional[Dict[str, Any]] = None
    most_executed_scenario: Optional[Dict[str, Any]] = None
    top_forecast_model: Optional[Dict[str, Any]] = None
    top_warehouse: Optional[Dict[str, Any]] = None
    top_region: Optional[Dict[str, Any]] = None


# ============================================================================
# DASHBOARD TRENDS
# ============================================================================

class DashboardTrendResponse(BaseModel):
    labels: List[str]
    values: List[float]
    counts: Optional[List[int]] = None
    average: float
    total: float
    period: str


# ============================================================================
# COMPARISON HISTORY
# ============================================================================

class ComparisonHistoryItem(BaseModel):
    comparison_id: str
    scenario_count: int
    best_scenario_id: Optional[int] = None
    created_at: datetime
    summary: Dict[str, Any]


class ComparisonHistoryResponse(BaseModel):
    total: int
    page: int
    pages: int
    items: List[ComparisonHistoryItem]


# ============================================================================
# SCENARIO HISTORY
# ============================================================================

class ScenarioHistoryItem(BaseModel):
    run_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    progress: float
    error_message: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime


class ScenarioHistoryResponse(BaseModel):
    history: List[ScenarioHistoryItem]
    count: int


# ============================================================================
# RECOMMENDATION DETAILS
# ============================================================================

class ScenarioRecommendationResponse(BaseModel):
    id: int
    sku: str
    title: Optional[str] = None
    description: Optional[str] = None
    priority: str
    recommendation_type: str
    ai_confidence: Optional[float] = None
    estimated_savings: Optional[float] = None
    status: str
    action_label: Optional[str] = None
    created_at: datetime


class ScenarioRecommendationsResponse(BaseModel):
    recommendations: List[ScenarioRecommendationResponse]
    count: int