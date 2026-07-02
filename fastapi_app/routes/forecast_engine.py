from fastapi import APIRouter, Query, Depends
from typing import Any
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.models.auth_model import User
from fastapi_app.services.forecast.forecast_engine_service import get_forecast_engine_report

router = APIRouter(prefix="/api/forecast-engine", tags=["Forecast Engine"])


@router.get("/report")
def forecast_engine_report(
    path: str | None = Query(None, description="Path to dataset CSV"),
    forecast_steps: int = Query(7, ge=1),
    model_type: str | None = Query(None, description="Model to return: arima, xgboost, lstm, prophet"),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return get_forecast_engine_report(path=path, forecast_steps=forecast_steps, model_type=model_type)
