from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.services.dashboard.dashboard_service import DashboardService
from fastapi_app.schemas.dashboard_schema import (
    DashboardSummary,
    DemandTrend,
    RegionalForecastData,
    WarehouseDistribution,
    AIInsights,
    LiveAlerts,
    TopSKUs,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/dashboard/summary
    
    Returns overall dashboard summary metrics:
    - Total SKUs
    - Total warehouses
    - Total forecasts
    - Total recommendations
    - Critical alerts count
    - System health score (0-100)
    """
    return DashboardService.get_summary(db)


@router.get("/demand-trend", response_model=DemandTrend)
def get_demand_trend(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/dashboard/demand-trend
    
    Returns demand trend analysis:
    - Trend points with date, demand, forecast, variance
    - Average demand
    - Peak demand
    - Minimum demand
    - Forecast accuracy percentage
    
    Query parameters:
    - days: Number of days to analyze (1-365, default 30)
    """
    return DashboardService.get_demand_trend(db, days=days)


@router.get("/regional-forecast", response_model=RegionalForecastData)
def get_regional_forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/dashboard/regional-forecast
    
    Returns regional forecast data:
    - List of forecasts by region and SKU
    - Forecasted demand per region
    - Confidence scores
    - Trend indicators
    """
    return DashboardService.get_regional_forecast(db)


@router.get("/warehouse-distribution", response_model=WarehouseDistribution)
def get_warehouse_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/dashboard/warehouse-distribution
    
    Returns warehouse inventory distribution:
    - Current stock levels per warehouse
    - Safety stock levels
    - Reorder points
    - Inventory status (healthy, warning, critical, excess)
    - Total stock value
    """
    return DashboardService.get_warehouse_distribution(db)


@router.get("/ai-insights", response_model=AIInsights)
def get_ai_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/dashboard/ai-insights
    
    Returns AI-generated insights based on current data:
    - Demand trend insights
    - Excess/shortage warnings
    - Critical alert summaries
    - Actionable recommendations
    - Priority levels
    """
    return DashboardService.get_ai_insights(db)


@router.get("/live-alerts", response_model=LiveAlerts)
def get_live_alerts(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of alerts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/dashboard/live-alerts
    
    Returns live alerts:
    - Recent alerts sorted by timestamp
    - Alerts grouped by severity (critical, warning, info)
    - Unread alert counts
    - Alert details (title, message, category, creation time)
    
    Query parameters:
    - limit: Maximum number of alerts to return (1-100, default 10)
    """
    return DashboardService.get_live_alerts(db, limit=limit)


@router.get("/top-skus", response_model=TopSKUs)
def get_top_skus(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of SKUs to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/dashboard/top-skus
    
    Returns top SKUs by demand and performance:
    - SKU identifier and name
    - Total and forecasted demand
    - Current stock levels
    - Turnover rates
    - Revenue impact indicators
    
    Query parameters:
    - limit: Maximum number of SKUs to return (1-50, default 10)
    """
    return DashboardService.get_top_skus(db, limit=limit)
