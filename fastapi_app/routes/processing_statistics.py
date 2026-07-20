#fastapi_app/routes/processing_statistics.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.services.data_processing.processing_statistics_service import ProcessingStatisticsService

router = APIRouter(prefix="/api/processing/statistics", tags=["Processing Statistics"])


@router.get("/")
def get_processing_statistics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get processing statistics."""
    return ProcessingStatisticsService.get_statistics(db, days)


@router.get("/chart")
def get_processing_chart(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chart data for processing jobs."""
    return ProcessingStatisticsService.get_chart_data(db, days)