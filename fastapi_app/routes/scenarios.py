# fastapi_app/routes/scenarios.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body, Response
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.scenario_model import Scenario, ScenarioResult
from fastapi_app.schemas.scenario_schema import (
    ScenarioCreate,
    ScenarioResponse,
    ScenarioUpdate,
    ScenarioRunResponse,
    ScenarioProgressResponse,
    ScenarioMetricsResponse,
    ScenarioTableResponse,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    ScenarioCardResponse,
    StockoutSKUResponse,
    AllSKUResponse,
    ScenarioFilter,
    ScenarioChartResponse,
    ScenarioSummaryResponse,
    BulkDeleteRequest,
    ScenarioDashboardCardsResponse,
)
from fastapi_app.services.scenario.scenario_service import ScenarioService
from fastapi_app.services.scenario.comparison_service import ComparisonService
from fastapi_app.services.scenario.export_service import ExportService

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

@router.get("", response_model=List[ScenarioResponse])
def list_scenarios(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    region: Optional[str] = None,
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    sku: Optional[str] = None,
    forecast_model: Optional[str] = None,
    created_by: Optional[int] = None,
    last_run_status: Optional[str] = None,
    sort: str = Query("-created_at"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List scenarios with filters and pagination."""
    filter_params = ScenarioFilter(
        search=search,
        status=status,
        region=region,
        warehouse=warehouse,
        category=category,
        sku=sku,
        forecast_model=forecast_model,
        created_by=created_by,
        last_run_status=last_run_status,
        sort=sort
    )
    result = ScenarioService.get_all_scenarios(db, filter_params, page, limit)
    return result["items"]


@router.post("", response_model=ScenarioResponse)
def create_scenario(
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new scenario."""
    try:
        return ScenarioService.create_scenario(db, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{scenario_id}/duplicate", response_model=ScenarioResponse)
def duplicate_scenario(
    scenario_id: int,
    name: Optional[str] = Query(None, description="Name for the duplicated scenario"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Duplicate an existing scenario."""
    scenario = ScenarioService.duplicate_scenario(db, scenario_id, name, current_user.id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.delete("/bulk", response_model=dict)
def bulk_delete_scenarios(
    request: BulkDeleteRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk delete scenarios."""
    result = ScenarioService.bulk_delete_scenarios(db, request.scenario_ids)
    return {
        "deleted_count": result["deleted"],
        "failed_count": result["failed"],
        "message": f"Deleted {result['deleted']} scenarios"
    }


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = ScenarioService.update_scenario(db, scenario_id, payload)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.patch("/{scenario_id}/parameters", response_model=ScenarioResponse)
def adjust_parameters(
    scenario_id: int,
    payload: ScenarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adjust scenario parameters (demand_surge, discount, etc.)"""
    scenario = ScenarioService.update_scenario(db, scenario_id, payload)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not ScenarioService.delete_scenario(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"deleted": True}


# ============================================================================
# RUN SIMULATION
# ============================================================================

@router.post("/{scenario_id}/run", response_model=ScenarioRunResponse)
def run_scenario(
    scenario_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a scenario simulation asynchronously."""
    try:
        run = ScenarioService.run_scenario_async(db, scenario_id, background_tasks, current_user.id)
        if not run:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/run/{run_id}", response_model=ScenarioProgressResponse)
def get_run_progress(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get simulation run progress."""
    progress = ScenarioService.get_progress(db, run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Run not found")
    return progress


@router.post("/run/{run_id}/cancel")
def cancel_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a running simulation."""
    if not ScenarioService.cancel_run(db, run_id):
        raise HTTPException(status_code=404, detail="Run not found or cannot be cancelled")
    return {"message": "Run cancelled successfully"}


@router.post("/run/{run_id}/retry", response_model=ScenarioRunResponse)
def retry_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed simulation."""
    run = ScenarioService.retry_run(db, run_id, current_user.id, background_tasks)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# ============================================================================
# PROGRESS
# ============================================================================

@router.get("/{scenario_id}/progress", response_model=ScenarioProgressResponse)
def get_progress(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scenario progress."""
    scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return ScenarioProgressResponse(
        run_id=str(scenario.id),
        status=scenario.status.value if hasattr(scenario.status, 'value') else str(scenario.status),
        progress=scenario.progress,
        current_step=None,
        started_at=scenario.last_run_at,
        estimated_completion=None
    )


# ============================================================================
# HISTORY
# ============================================================================

@router.get("/{scenario_id}/history")
def get_scenario_history(
    scenario_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scenario execution history."""
    history = ScenarioService.get_scenario_history(db, scenario_id, limit)
    return {"history": history, "count": len(history)}


# ============================================================================
# METRICS & SUMMARY
# ============================================================================

@router.get("/{scenario_id}/metrics", response_model=ScenarioMetricsResponse)
def get_metrics(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scenario metrics."""
    metrics = ScenarioService.get_metrics(db, scenario_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="No results found for this scenario")
    return metrics


@router.get("/{scenario_id}/summary", response_model=ScenarioSummaryResponse)
def get_summary(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scenario summary."""
    scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    metrics = ScenarioService.get_metrics(db, scenario_id)
    
    return ScenarioSummaryResponse(
        scenario_id=scenario.id,
        name=scenario.name,
        status=scenario.status.value if hasattr(scenario.status, 'value') else str(scenario.status),
        metrics=metrics,
        created_at=scenario.created_at
    )


# ============================================================================
# CHARTS
# ============================================================================

@router.get("/{scenario_id}/forecast-chart", response_model=ScenarioChartResponse)
def get_forecast_chart(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get forecast chart data."""
    chart = ScenarioService.get_forecast_chart(db, scenario_id)
    if not chart:
        raise HTTPException(status_code=404, detail="No forecast data found")
    return chart


@router.get("/{scenario_id}/inventory-chart", response_model=ScenarioChartResponse)
def get_inventory_chart(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get inventory chart data."""
    chart = ScenarioService.get_inventory_chart(db, scenario_id)
    if not chart:
        raise HTTPException(status_code=404, detail="No inventory data found")
    return chart


# ============================================================================
# STOCKOUT & ALL SKUS
# ============================================================================

@router.get("/{scenario_id}/stockout-skus", response_model=List[StockoutSKUResponse])
def get_stockout_skus(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get stockout SKUs for a scenario."""
    skus = ScenarioService.get_stockout_skus(db, scenario_id)
    return skus


@router.get("/{scenario_id}/all-skus", response_model=List[AllSKUResponse])
def get_all_skus(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all SKU data for a scenario."""
    skus = ScenarioService.get_all_skus(db, scenario_id)
    return skus


# ============================================================================
# RECOMMENDATIONS
# ============================================================================

@router.get("/{scenario_id}/recommendations")
def get_recommendations(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full recommendation details for a scenario."""
    recs = ScenarioService.get_recommendations(db, scenario_id)
    return {"recommendations": recs, "count": len(recs)}


# ============================================================================
# TABLE
# ============================================================================

@router.get("/table", response_model=ScenarioTableResponse)
def get_table(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scenario table data."""
    return ScenarioService.get_table_data(db, page, limit)


# ============================================================================
# CARDS
# ============================================================================

@router.get("/cards", response_model=ScenarioCardResponse)
def get_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scenario cards."""
    return ScenarioService.get_cards(db)


@router.get("/dashboard/cards", response_model=ScenarioDashboardCardsResponse)
def get_dashboard_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics cards."""
    return ScenarioService.get_dashboard_cards(db)


@router.get("/dashboard/analytics")
def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive dashboard analytics."""
    return ScenarioService.get_dashboard_analytics(db)


# ============================================================================
# DASHBOARD TRENDS
# ============================================================================

@router.get("/dashboard/revenue-trend")
def get_revenue_trend(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get revenue trend across all scenarios."""
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(ScenarioResult).filter(
        ScenarioResult.created_at >= start_date
    ).order_by(ScenarioResult.created_at).all()
    
    daily_data = {}
    for r in results:
        day = r.created_at.strftime("%Y-%m-%d")
        if day not in daily_data:
            daily_data[day] = {"revenue": 0, "count": 0}
        daily_data[day]["revenue"] += r.total_revenue or 0
        daily_data[day]["count"] += 1
    
    dates = sorted(daily_data.keys())
    revenue = [daily_data[d]["revenue"] for d in dates]
    counts = [daily_data[d]["count"] for d in dates]
    
    return {
        "labels": dates,
        "revenue": revenue,
        "counts": counts,
        "average": sum(revenue) / len(revenue) if revenue else 0,
        "total": sum(revenue),
        "period": f"{days} days"
    }


@router.get("/dashboard/demand-trend")
def get_demand_trend(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get demand trend across all scenarios."""
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(ScenarioResult).filter(
        ScenarioResult.created_at >= start_date
    ).order_by(ScenarioResult.created_at).all()
    
    daily_data = {}
    for r in results:
        day = r.created_at.strftime("%Y-%m-%d")
        if day not in daily_data:
            daily_data[day] = {"demand": 0, "count": 0}
        daily_data[day]["demand"] += r.total_demand or 0
        daily_data[day]["count"] += 1
    
    dates = sorted(daily_data.keys())
    demand = [daily_data[d]["demand"] for d in dates]
    counts = [daily_data[d]["count"] for d in dates]
    
    return {
        "labels": dates,
        "demand": demand,
        "counts": counts,
        "average": sum(demand) / len(demand) if demand else 0,
        "total": sum(demand),
        "period": f"{days} days"
    }


@router.get("/dashboard/risk-trend")
def get_risk_trend(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get risk trend across all scenarios."""
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(ScenarioResult).filter(
        ScenarioResult.created_at >= start_date
    ).order_by(ScenarioResult.created_at).all()
    
    daily_data = {}
    for r in results:
        day = r.created_at.strftime("%Y-%m-%d")
        if day not in daily_data:
            daily_data[day] = {"risk": 0, "count": 0}
        daily_data[day]["risk"] += r.stockout_risk or 0
        daily_data[day]["count"] += 1
    
    dates = sorted(daily_data.keys())
    risk = [daily_data[d]["risk"] / daily_data[d]["count"] if daily_data[d]["count"] > 0 else 0 for d in dates]
    counts = [daily_data[d]["count"] for d in dates]
    
    return {
        "labels": dates,
        "risk": risk,
        "counts": counts,
        "average": sum(risk) / len(risk) if risk else 0,
        "period": f"{days} days"
    }


@router.get("/dashboard/status-chart")
def get_status_chart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scenario status distribution."""
    from sqlalchemy import func
    
    status_counts = db.query(
        Scenario.status,
        func.count(Scenario.id)
    ).group_by(Scenario.status).all()
    
    return {
        "labels": [s[0].value if hasattr(s[0], 'value') else str(s[0]) for s in status_counts],
        "values": [s[1] for s in status_counts],
        "total": sum(s[1] for s in status_counts)
    }


@router.get("/dashboard/model-usage")
def get_model_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get forecast model usage distribution."""
    from sqlalchemy import func
    
    model_counts = db.query(
        Scenario.forecast_model,
        func.count(Scenario.id)
    ).group_by(Scenario.forecast_model).all()
    
    return {
        "labels": [m[0] for m in model_counts],
        "values": [m[1] for m in model_counts],
        "total": sum(m[1] for m in model_counts)
    }


# ============================================================================
# COMPARISON
# ============================================================================

@router.post("/compare", response_model=ScenarioComparisonResponse)
def compare_scenarios(
    request: ScenarioComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare multiple scenarios."""
    if len(request.scenario_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 scenarios to compare")
    
    return ComparisonService.compare_scenarios(db, request.scenario_ids)


@router.post("/quick-compare", response_model=ScenarioComparisonResponse)
def quick_compare(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quick compare latest 3 scenarios."""
    result = ScenarioService.get_all_scenarios(db)
    scenarios = result["items"]
    if len(scenarios) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 scenarios to compare")
    
    scenario_ids = [s.id for s in scenarios[:3]]
    return ComparisonService.compare_scenarios(db, scenario_ids)


@router.get("/comparison/history")
def get_comparison_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get comparison history with pagination."""
    return ComparisonService.get_comparison_history(db, limit, offset)


@router.delete("/comparison/{comparison_id}")
def delete_comparison(
    comparison_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comparison."""
    if not ComparisonService.delete_comparison(db, comparison_id):
        raise HTTPException(status_code=404, detail="Comparison not found")
    return {"deleted": True}


@router.patch("/comparison/{comparison_id}")
def update_comparison(
    comparison_id: str,
    name: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update comparison name."""
    result = ComparisonService.update_comparison(db, comparison_id, name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ============================================================================
# EXPORT
# ============================================================================

@router.get("/{scenario_id}/export/csv")
def export_csv(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export scenario to CSV."""
    try:
        return ExportService.export_csv(db, scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{scenario_id}/export/excel")
def export_excel(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export scenario to Excel."""
    try:
        return ExportService.export_excel(db, scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{scenario_id}/export/pdf")
def export_pdf(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export scenario to PDF."""
    try:
        return ExportService.export_pdf(db, scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))