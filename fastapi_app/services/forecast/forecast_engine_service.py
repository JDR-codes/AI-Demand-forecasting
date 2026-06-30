from typing import Any
from fastapi_app.services.forecast.forecast_service import auto_forecast_report


def get_forecast_engine_report(path: str | None = None, forecast_steps: int = 7) -> dict[str, Any]:
    return auto_forecast_report(path=path, forecast_steps=forecast_steps)
