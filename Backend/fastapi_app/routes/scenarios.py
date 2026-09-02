# fastapi_app/routes/scenarios.py
"""
Scenario Router - Simplified endpoints matching Figma.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user, require_permission_dep
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.scenario_schema import (
    ScenarioCreate,
    ScenarioResponse,
    ScenarioUpdate,
    RunResponse,
    ProgressResponse,
    DashboardResponse,
    ForecastChartResponse,
    InventoryChartResponse,
    StockoutSKUResponse,
    RecommendationResponse,
    ComparisonRequest,
    ComparisonResponse,
    ScenarioFilter,
    ScenarioListResponse
)
from fastapi_app.services.scenario.scenario_service import ScenarioService
from fastapi_app.services.scenario.comparison_service import ComparisonService
from fastapi_app.services.scenario.export_service import ExportService

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


# ============================================================================
# 1. LIST & CREATE SCENARIOS (Base prefix routes)
# ============================================================================

@router.get("", response_model=ScenarioListResponse)
def list_scenarios(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    region: Optional[str] = None,
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    sku: Optional[str] = None,
    sort: str = Query("-created_at"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """List scenarios with filters and pagination."""
    filter_params = ScenarioFilter(
        search=search,
        status=status,
        region=region,
        warehouse=warehouse,
        category=category,
        sku=sku,
        sort=sort
    )
    return ScenarioService.get_all_scenarios(db, filter_params, page, limit)


@router.post("", response_model=ScenarioResponse)
def create_scenario(
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:run")),
):
    """Create a new scenario."""
    try:
        return ScenarioService.create_scenario(db, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 2. STATIC UTILITY ROUTES (Defined before dynamic path parameters)
# ============================================================================

@router.post("/compare", response_model=ComparisonResponse)
def compare_scenarios(
    request: ComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:run")),
):
    """Compare multiple scenarios."""
    if len(request.scenario_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 scenarios to compare")
    
    result = ComparisonService.compare_scenarios(db, request.scenario_ids)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ============================================================================
# 3. RUN LIFECYCLE MANAGEMENT (Dynamic runs routes)
# ============================================================================

@router.post("/run/{run_id}/cancel")
def cancel_simulation_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:run")),
):
    """Cancel a running simulation."""
    if not ScenarioService.cancel_run(db, run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return {"message": "Simulation run cancelled successfully"}


@router.get("/run/{run_id}", response_model=ProgressResponse)
def get_progress(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get simulation progress."""
    progress = ScenarioService.get_progress(db, run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Run not found")
    return progress


# ============================================================================
# 4. SCENARIO DETAILED READ, WRITE & SIMULATE
# ============================================================================

@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get a scenario by ID."""
    scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:run")),
):
    """Update a scenario."""
    scenario = ScenarioService.update_scenario(db, scenario_id, payload)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.post("/{scenario_id}/run", response_model=RunResponse)
def run_scenario(
    scenario_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:run")),
):
    """Run a scenario simulation asynchronously."""
    try:
        run = ScenarioService.run_scenario_async(db, scenario_id, background_tasks, current_user.id)
        if not run:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 5. SIMULATION DASHBOARD, ANALYSIS & METRICS
# ============================================================================

@router.get("/{scenario_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get complete dashboard data."""
    dashboard = ScenarioService.get_dashboard(db, scenario_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="No results found for this scenario")
    return dashboard


@router.get("/{scenario_id}/forecast", response_model=ForecastChartResponse)
def get_forecast_chart(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get forecast chart data."""
    chart = ScenarioService.get_forecast_chart(db, scenario_id)
    if not chart:
        raise HTTPException(status_code=404, detail="No forecast data found")
    return chart


@router.get("/{scenario_id}/inventory", response_model=InventoryChartResponse)
def get_inventory_chart(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get inventory chart data."""
    chart = ScenarioService.get_inventory_chart(db, scenario_id)
    if not chart:
        raise HTTPException(status_code=404, detail="No inventory data found")
    return chart


@router.get("/{scenario_id}/stockouts", response_model=List[StockoutSKUResponse])
def get_stockouts(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get stockout table data."""
    stockouts = ScenarioService.get_stockouts(db, scenario_id)
    return stockouts


@router.get("/{scenario_id}/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get recommendations for a scenario."""
    return ScenarioService.get_recommendations(db, scenario_id)


@router.get("/{scenario_id}/runs", response_model=List[ProgressResponse])
def get_scenario_run_history(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Get the history of simulation runs for a scenario."""
    runs = ScenarioService.get_scenario_runs(db, scenario_id)
    return [
        ProgressResponse(
            run_id=r.run_id,
            status=r.status,
            progress=r.progress,
            current_step=r.current_step,
            step_number=r.step_number,
            total_steps=r.total_steps,
            message=r.logs[-1]["message"] if r.logs else None,
            started_at=r.started_at
        )
        for r in runs
    ]


@router.post("/{scenario_id}/apply")
def apply_scenario_settings(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:run")),
):
    """Promote scenario parameters and execute recommended transfers/reorders."""
    if not ScenarioService.apply_scenario(db, scenario_id, current_user.id):
        raise HTTPException(status_code=400, detail="Failed to apply scenario settings or no recommendations found")
    return {"message": "Scenario settings and recommendations applied successfully"}


# ============================================================================
# 6. SIMULATION REPORTS EXPORT
# ============================================================================

@router.get("/{scenario_id}/export/csv")
def export_csv(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:read")),
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
    current_user: User = Depends(require_permission_dep("simulation:read")),
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
    current_user: User = Depends(require_permission_dep("simulation:read")),
):
    """Export scenario to PDF."""
    try:
        return ExportService.export_pdf(db, scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# 7. CLEANUP
# ============================================================================

@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("simulation:delete")),
):
    """Delete a scenario."""
    if not ScenarioService.delete_scenario(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"deleted": True}