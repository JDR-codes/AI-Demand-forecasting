from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi_app.models.forecast_model import Forecast
from fastapi_app.models.recommendation_model import Recommendation
from fastapi_app.models.alert_model import Alert, AlertSeverity
from fastapi_app.models.inventory_model import InventorySKU, WarehouseInventory
from fastapi_app.schemas.dashboard_schema import (
    DashboardSummary,
    SummaryMetrics,
    DemandTrend,
    DemandTrendPoint,
    RegionalForecastData,
    RegionalForecast,
    WarehouseDistribution,
    WarehouseInventory as WarehouseInventorySchema,
    AIInsights,
    AIInsight,
    LiveAlerts,
    Alert as AlertSchema,
    TopSKUs,
    TopSKU,
)


class DashboardService:
    """Service for aggregating dashboard data from multiple sources"""

    @staticmethod
    def get_summary(db: Session) -> DashboardSummary:
        """Get overall summary metrics for the dashboard"""
        
        # Count total SKUs
        total_skus = db.query(func.count(InventorySKU.id)).scalar() or 0
        
        # Count total warehouses (model uses `warehouse` column)
        total_warehouses = db.query(WarehouseInventory.warehouse).distinct().count() or 0
        
        # Count total forecasts
        total_forecasts = db.query(func.count(Forecast.id)).scalar() or 0
        
        # Count total recommendations
        total_recommendations = db.query(func.count(Recommendation.id)).scalar() or 0
        
        # Count critical alerts
        critical_alerts = db.query(func.count(Alert.id)).filter(
            Alert.severity == AlertSeverity.CRITICAL
        ).scalar() or 0
        
        # Calculate health score (0-100)
        health_score = DashboardService._calculate_health_score(
            db, total_skus, total_warehouses, critical_alerts
        )
        
        metrics = SummaryMetrics(
            total_skus=total_skus,
            total_warehouses=total_warehouses,
            total_forecasts=total_forecasts,
            total_recommendations=total_recommendations,
            critical_alerts=critical_alerts,
            health_score=health_score,
        )
        
        return DashboardSummary(metrics=metrics, timestamp=datetime.utcnow())

    @staticmethod
    def get_demand_trend(db: Session, days: int = 30) -> DemandTrend:
        """Get demand trend data for the past N days"""
        
        # Query forecasts from the past N days
        start_date = datetime.utcnow() - timedelta(days=days)
        forecasts = db.query(Forecast).filter(
            Forecast.forecast_date >= start_date
        ).order_by(Forecast.forecast_date).all()
        
        if not forecasts:
            return DemandTrend(
                trend=[],
                avg_demand=0.0,
                peak_demand=0.0,
                min_demand=0.0,
                forecast_accuracy=0.0,
            )
        
        # Build trend data
        trend_points = []
        demands = []
        
        for forecast in forecasts:
            trend_points.append(
                DemandTrendPoint(
                    date=forecast.forecast_date.strftime("%Y-%m-%d"),
                    demand=forecast.predicted_demand,
                    forecast=forecast.predicted_demand,
                    variance=0.0,  # Can be calculated if actuals available
                )
            )
            demands.append(forecast.predicted_demand)
        
        avg_demand = sum(demands) / len(demands) if demands else 0.0
        peak_demand = max(demands) if demands else 0.0
        min_demand = min(demands) if demands else 0.0
        
        # Mock accuracy; in production, compare actuals vs forecasts
        forecast_accuracy = 85.0
        
        return DemandTrend(
            trend=trend_points,
            avg_demand=avg_demand,
            peak_demand=peak_demand,
            min_demand=min_demand,
            forecast_accuracy=forecast_accuracy,
        )

    @staticmethod
    def get_regional_forecast(db: Session) -> RegionalForecastData:
        """Get regional forecast data"""
        
        # Get latest forecasts grouped by region
        forecasts = db.query(Forecast).order_by(Forecast.forecast_date.desc()).limit(50).all()
        
        regional_forecasts = []
        seen = set()
        
        for forecast in forecasts:
            key = (forecast.region, forecast.sku)
            if key not in seen:
                regional_forecasts.append(
                    RegionalForecast(
                        region=forecast.region or "Unknown",
                        sku=forecast.sku or "Unknown",
                        forecasted_demand=forecast.predicted_demand,
                        confidence=forecast.confidence_score or 0.85,
                        trend="stable",  # Can be calculated from historical data
                    )
                )
                seen.add(key)
            
            if len(regional_forecasts) >= 10:
                break
        
        return RegionalForecastData(
            forecasts=regional_forecasts,
            total_regions=len(set(f.region for f in forecasts if f.region)),
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def get_warehouse_distribution(db: Session) -> WarehouseDistribution:
        """Get warehouse inventory distribution"""
        
        warehouses = db.query(WarehouseInventory).limit(20).all()
        
        inventory_schemas = []
        total_stock_value = 0.0
        
        for warehouse in warehouses:
            # Normalize nullable fields to avoid runtime TypeErrors
            current_stock = warehouse.current_stock or 0.0
            safety_stock = warehouse.safety_stock or 0.0
            reorder_point = warehouse.reorder_point or 0.0

            inventory_schemas.append(
                WarehouseInventorySchema(
                    warehouse_id=warehouse.warehouse or "Unknown",
                    sku=warehouse.sku or "Unknown",
                    current_stock=current_stock,
                    safety_stock=safety_stock,
                    reorder_point=reorder_point,
                    status=DashboardService._get_inventory_status_safe(current_stock, safety_stock),
                )
            )
            total_stock_value += (warehouse.current_stock or 0.0) * 50.0  # Mock unit price
        
        return WarehouseDistribution(
            inventory=inventory_schemas,
            total_warehouses=db.query(WarehouseInventory.warehouse).distinct().count() or 1,
            total_stock_value=total_stock_value,
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def get_ai_insights(db: Session) -> AIInsights:
        """Generate AI insights from current data"""
        
        insights = []
        
        # Insight 1: High demand trend
        high_demand_forecasts = db.query(func.count(Forecast.id)).filter(
            Forecast.predicted_demand > 1000
        ).scalar() or 0
        
        if high_demand_forecasts > 5:
            insights.append(
                AIInsight(
                    title="High Demand Trend Detected",
                    description="Multiple SKUs showing elevated demand forecasts.",
                    impact="high",
                    recommendation="Increase procurement orders and safety stock levels.",
                    priority="critical",
                )
            )
        
        # Insight 2: Excess stock warning
        excess_count = db.query(func.count(WarehouseInventory.id)).filter(
            WarehouseInventory.current_stock > (WarehouseInventory.safety_stock * 2)
        ).scalar() or 0
        
        if excess_count > 3:
            insights.append(
                AIInsight(
                    title="Excess Stock Alert",
                    description=f"{excess_count} warehouse locations have excess inventory.",
                    impact="medium",
                    recommendation="Consider transfers, promotions, or markdown strategies.",
                    priority="high",
                )
            )
        
        # Insight 3: Critical alerts
        critical_count = db.query(func.count(Alert.id)).filter(
            Alert.severity == AlertSeverity.CRITICAL
        ).scalar() or 0
        
        if critical_count > 0:
            insights.append(
                AIInsight(
                    title="Critical Alerts Require Attention",
                    description=f"{critical_count} critical alerts are pending action.",
                    impact="critical",
                    recommendation="Review and address critical alerts immediately.",
                    priority="critical",
                )
            )
        
        # Default insight if none generated
        if not insights:
            insights.append(
                AIInsight(
                    title="System Operating Normally",
                    description="All metrics are within normal ranges.",
                    impact="low",
                    recommendation="Continue monitoring.",
                    priority="info",
                )
            )
        
        return AIInsights(insights=insights, generated_at=datetime.utcnow())

    @staticmethod
    def get_live_alerts(db: Session, limit: int = 10) -> LiveAlerts:
        """Get live alerts grouped by severity"""
        
        alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(limit).all()
        
        alert_schemas = [
            AlertSchema(
                alert_id=alert.id,
                title=alert.title or "Alert",
                severity=alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity),
                category=alert.category.value if hasattr(alert.category, 'value') else str(alert.category),
                message=alert.message or "",
                created_at=alert.created_at,
                is_read=alert.is_read or False,
            )
            for alert in alerts
        ]
        
        critical_count = db.query(func.count(Alert.id)).filter(
            Alert.severity == AlertSeverity.CRITICAL
        ).scalar() or 0
        
        warning_count = db.query(func.count(Alert.id)).filter(
            Alert.severity == AlertSeverity.WARNING
        ).scalar() or 0
        
        info_count = db.query(func.count(Alert.id)).filter(
            Alert.severity == AlertSeverity.INFO
        ).scalar() or 0
        
        total_count = db.query(func.count(Alert.id)).scalar() or 0
        
        return LiveAlerts(
            alerts=alert_schemas,
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            total_count=total_count,
        )

    @staticmethod
    def get_top_skus(db: Session, limit: int = 10) -> TopSKUs:
        """Get top SKUs by demand and turnover"""
        
        # Query top SKUs by forecast demand
        top_skus_query = db.query(Forecast).order_by(
            Forecast.predicted_demand.desc()
        ).limit(limit).all()
        
        top_skus = []
        seen = set()
        
        for forecast in top_skus_query:
            if forecast.sku and forecast.sku not in seen:
                # Get warehouse inventory for this SKU
                inventory = db.query(WarehouseInventory).filter(
                    WarehouseInventory.sku == forecast.sku
                ).first()
                
                current_stock = inventory.current_stock if inventory else 0.0
                
                top_skus.append(
                    TopSKU(
                        sku=forecast.sku,
                        name=f"Product {forecast.sku}",
                        total_demand=forecast.predicted_demand,
                        forecast_demand=forecast.predicted_demand,
                        current_stock=current_stock,
                        turnover_rate=0.85,  # Mock turnover rate
                        revenue_impact="high",
                    )
                )
                seen.add(forecast.sku)
        
        return TopSKUs(top_skus=top_skus, timestamp=datetime.utcnow())

    # ─── Helper methods ───

    @staticmethod
    def _calculate_health_score(db: Session, total_skus: int, total_warehouses: int, critical_alerts: int) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0
        
        # Deduct for critical alerts
        score -= critical_alerts * 5.0
        
        # Deduct for excess inventory
        excess_count = db.query(func.count(WarehouseInventory.id)).filter(
            WarehouseInventory.current_stock > (WarehouseInventory.safety_stock * 2)
        ).scalar() or 0
        score -= min(excess_count * 2, 20.0)
        
        # Deduct for low inventory
        low_count = db.query(func.count(WarehouseInventory.id)).filter(
            WarehouseInventory.current_stock < WarehouseInventory.safety_stock
        ).scalar() or 0
        score -= min(low_count * 3, 25.0)
        
        return max(score, 0.0)

    @staticmethod
    def _get_inventory_status(warehouse: WarehouseInventory) -> str:
        """Determine inventory status: healthy, warning, critical"""
        # Legacy safe method retained for compatibility (kept but not used by new callers)
        current = warehouse.current_stock or 0.0
        safety = warehouse.safety_stock or 0.0
        if safety == 0.0:
            return "healthy"
        if current < safety:
            return "critical"
        elif current < safety * 1.5:
            return "warning"
        elif current > safety * 2:
            return "excess"
        else:
            return "healthy"

    @staticmethod
    def _get_inventory_status_safe(current_stock: float, safety_stock: float) -> str:
        """Null-safe inventory status helper using numeric values."""
        current = current_stock or 0.0
        safety = safety_stock or 0.0
        if safety == 0.0:
            return "healthy"
        if current < safety:
            return "critical"
        elif current < safety * 1.5:
            return "warning"
        elif current > safety * 2:
            return "excess"
        else:
            return "healthy"
