from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from typing import List
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.report_schema import (
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
)
from fastapi_app.services.report.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("", response_model=List[ReportListResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/reports

    Return all previously generated reports (newest first).
    """
    return ReportService.list_reports(db)


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /api/v1/reports/generate

    Generate a new report and return it fully populated.

    **report_type** options:
    - `forecast_summary` — all forecasts (filter by sku / warehouse / region)
    - `inventory_health` — warehouse stock, reorder points, excess stock, transfers, safety stock
    - `recommendation_summary` — procurement/reorder recommendations (filter by status / priority)
    - `scenario_comparison` — all scenarios with run outputs and side-by-side comparison
    - `full_system` — all four sections combined with an executive summary

    **format**: `json` (default) | `csv`

    **parameters** examples:
    ```json
    { "sku": "SKU-001", "warehouse": "WH-A", "limit": 50 }
    ```
    """
    try:
        report = ReportService.generate_report(db, payload, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return report


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/reports/{report_id}/download

    Download the report as a file attachment (JSON or CSV based on format
    chosen at generation time).
    """
    report = ReportService.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        content, media_type, filename = ReportService.get_download_content(report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
