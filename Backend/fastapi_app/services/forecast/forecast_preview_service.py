#fastapi_app/services/forecast/forecast_preview_service.py

"""
Forecast Preview Service - Dataset preview only.
"""
from typing import Dict, Any

from fastapi_app.services.forecast.forecast_service import prepare_series


class ForecastPreviewService:
    """Service for dataset preview."""
    
    @staticmethod
    def preview_dataset(path: str, forecast_steps: int = 7) -> Dict[str, Any]:
        """Preview a dataset before forecasting."""
        try:
            series = prepare_series(path=path)
            
            return {
                "series_length": len(series),
                "series_start": str(series.index[0]) if len(series) > 0 else None,
                "series_end": str(series.index[-1]) if len(series) > 0 else None,
                "mean": float(series.mean()) if len(series) > 0 else None,
                "std": float(series.std()) if len(series) > 0 else None,
                "min": float(series.min()) if len(series) > 0 else None,
                "max": float(series.max()) if len(series) > 0 else None,
                "forecast_steps": forecast_steps,
                "last_10_values": [float(x) for x in series.tail(10).tolist()]
            }
        except Exception as e:
            return {"error": str(e)}