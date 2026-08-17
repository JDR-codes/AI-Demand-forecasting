# fastapi_app/schemas/scenario_schema.py
"""
Scenario Schemas - Simplified UI-focused schemas.
"""
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
# CREATE SCENARIO
# ============================================================================

class ScenarioCreate(BaseModel):
    """Used by Create Scenario page."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    
    # Filters
    region: Optional[str] = Field(None, max_length=100)
    warehouse: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    sku: Optional[str] = Field(None, max_length=100)
    time_horizon: int = Field(30, ge=1, le=365)
    
    # Simulation Inputs
    demand_surge: float = Field(0.0, ge=-50, le=100)
    discount: float = Field(0.0, ge=0, le=100)
    price_change: float = Field(0.0, ge=-50, le=50)
    supply_delay: int = Field(0, ge=0, le=30)
    seasonal_impact: float = Field(0.0, ge=-50, le=50)
    
    # Forecast Model
    forecast_model: str = Field("arima", pattern="^(arima|xgboost|lstm|prophet|auto)$")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class ScenarioUpdate(BaseModel):
    """Same fields as create, all optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    region: Optional[str] = Field(None, max_length=100)
    warehouse: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    sku: Optional[str] = Field(None, max_length=100)
    time_horizon: Optional[int] = Field(None, ge=1, le=365)
    demand_surge: Optional[float] = Field(None, ge=-50, le=100)
    discount: Optional[float] = Field(None, ge=0, le=100)
    price_change: Optional[float] = Field(None, ge=-50, le=50)
    supply_delay: Optional[int] = Field(None, ge=0, le=30)
    seasonal_impact: Optional[float] = Field(None, ge=-50, le=50)
    forecast_model: Optional[str] = Field(None, pattern="^(arima|xgboost|lstm|prophet|auto)$")
    status: Optional[ScenarioStatus] = None


class ScenarioResponse(BaseModel):
    """Return only UI fields."""
    id: int
    name: str
    description: Optional[str] = None
    region: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    time_horizon: int
    forecast_model: str
    demand_surge: float
    discount: float
    price_change: float
    supply_delay: int
    seasonal_impact: float
    status: ScenarioStatus
    progress: float
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# FILTER
# ============================================================================

class ScenarioFilter(BaseModel):
    """Simplified filter for listing scenarios."""
    search: Optional[str] = None
    status: Optional[str] = None
    region: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    sort: Optional[str] = "-created_at"


class ScenarioListResponse(BaseModel):
    total: int
    page: int
    pages: int
    items: List[ScenarioResponse]


# ============================================================================
# RUN
# ============================================================================

class RunResponse(BaseModel):
    """Returned when starting a simulation."""
    run_id: str
    scenario_id: int
    status: str
    progress: float
    step: Optional[str] = None
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    started_at: Optional[datetime] = None


class ProgressResponse(BaseModel):
    """Used for loading screen."""
    run_id: str
    status: str
    progress: float
    current_step: Optional[str] = None
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    message: Optional[str] = None
    started_at: Optional[datetime] = None


# ============================================================================
# DASHBOARD
# ============================================================================

class SummaryCardsResponse(BaseModel):
    demand_impact: Optional[float] = None
    inventory_impact: Optional[float] = None
    revenue_impact: Optional[float] = None
    stockout_risk: Optional[float] = None
    total_demand: Optional[float] = None
    total_inventory: Optional[float] = None
    total_revenue: Optional[float] = None
    stockout_count: Optional[int] = 0


class ForecastChartResponse(BaseModel):
    labels: List[str]
    baseline: List[float]
    simulation: List[float]


class InventoryChartResponse(BaseModel):
    labels: List[str]
    baseline: List[float]
    simulation: List[float]


class RecommendationResponse(BaseModel):
    """Dedicated schema for recommendations."""
    id: int
    sku: str
    title: str
    description: Optional[str] = None
    priority: str
    recommendation_type: str
    ai_confidence: Optional[float] = None
    estimated_savings: Optional[float] = None
    action_label: Optional[str] = None


class StockoutSKUResponse(BaseModel):
    """Stockout table row matching UI columns."""
    sku: str
    product_name: Optional[str] = None
    demand: float
    shortage: float
    revenue_risk: float
    risk_level: str  # high, medium, low
    current_stock: Optional[float] = None
    recommended_quantity: Optional[float] = None
    lost_sales: Optional[float] = None


class DashboardResponse(BaseModel):
    """Complete dashboard data for scenario."""
    # Summary Cards
    summary_cards: SummaryCardsResponse
    
    # Forecast Chart
    forecast: ForecastChartResponse
    
    # Inventory Chart
    inventory: InventoryChartResponse
    
    # Stockout Table
    stockouts: List[StockoutSKUResponse]
    
    # Recommendations
    recommendations: List[RecommendationResponse]


# ============================================================================
# COMPARISON
# ============================================================================

class ComparisonRequest(BaseModel):
    scenario_ids: List[int] = Field(..., min_length=2, max_length=10)


class ComparisonResponse(BaseModel):
    """Comparison result."""
    comparison_id: str
    winner: Dict[str, Any]
    ranking: List[Dict[str, Any]]
    comparison_chart: Dict[str, Any]
    scenario_names: List[str]
    created_at: datetime