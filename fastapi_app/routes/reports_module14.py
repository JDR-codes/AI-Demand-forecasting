from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.report_schema import (
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
    SKUPerformanceResponse,
    SKUDetailsResponse,
)
from fastapi_app.services.report.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("", response_model=List[ReportListResponse])
def list_reports(
    search: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/reports

    Return all previously generated reports (newest first), optionally filtered by search query or category/type.
    """
    return ReportService.list_reports(db, search=search, category=category, skip=skip, limit=limit)


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /api/reports/generate

    report_type options:
    - `executive_summary` — high-level KPIs and insights only
    - `demand_summary` — demand overview, trends, key drivers
    - `forecast_summary` — all forecasts (filter by sku / warehouse / region)
    - `model_performance` — accuracy and diagnostics per forecasting model
    - `inventory_health` — warehouse stock, reorder points, excess stock, transfers, safety stock
    - `stockout_risk` — at-risk SKUs and recommendations
    - `recommendation_summary` — procurement/reorder recommendations (filter by status / priority)
    - `scenario_comparison` — all scenarios with run outputs and side-by-side comparison
    - `full_system` — all sections combined with an executive summary
    - `custom_report` — pass `parameters.sections` to pick which sections to include

    format: `json` (default) | `csv` | `pdf` | `excel`

    parameters examples:
    ```json
    {
      "sku": "SKU-001",
      "region": "West",
      "category": "Electronics",
      "date_range": "last_30_days",
      "limit": 50
    }
    ```
    """
    try:
        report = ReportService.generate_report(db, payload, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return report


@router.get("/sku-performance", response_model=List[SKUPerformanceResponse])
def get_sku_performance(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/reports/sku-performance

    Get SKU performance statistics for SKU reports grid tab.
    """
    return ReportService.get_sku_performance(db, search=search)


@router.get("/sku-details/{sku}", response_model=SKUDetailsResponse)
def get_sku_details(
    sku: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/reports/sku-details/{sku}

    Get detailed analysis of a single SKU.
    """
    res = ReportService.get_sku_details(db, sku)
    if not res:
        raise HTTPException(status_code=404, detail="SKU details not found")
    return res


@router.get("/overview-metrics", response_model=dict)
def get_overview_metrics(
    region: Optional[str] = None,
    category: Optional[str] = None,
    date_range: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/reports/overview-metrics?region=West&category=Electronics&date_range=last_30_days

    Live KPI cards for the Reports landing page header
    (Total Revenue Impact, Average Forecast Accuracy, Stockouts Prevented,
    Overstock Reduced) — computed fresh from current DB state, independent
    of any specific generated report. All filters are optional.
    """
    return ReportService.get_overview_metrics(
        db, region=region, category=category, date_range=date_range
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/reports/{report_id}

    Retrieve a specific report by id including its full data payload.
    """
    report = ReportService.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    format: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/reports/{report_id}/download

    Download the report as a file attachment. Supports format overrides (pdf, excel, csv, json).
    """
    report = ReportService.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        content, media_type, filename = ReportService.get_download_content(report, format_override=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )