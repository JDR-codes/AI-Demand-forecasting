#fastapi_app/services/forecast/forecast_metrics.py

"""
Forecast Metrics - Calculations only, no database queries.
"""
from typing import Dict, Any, List, Optional
import numpy as np


class ForecastMetricsService:  # ✅ Keep this class name (used by ForecastRunner)
    """Calculate forecast metrics - pure calculations."""
    
    @staticmethod
    def calculate_confidence_interval(
        forecast: List[float],
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Calculate confidence intervals for forecast."""
        if not forecast:
            return {"upper": [], "lower": [], "confidence_level": confidence_level}
        
        forecast_array = np.array(forecast)
        std = np.std(forecast_array)
        
        try:
            from scipy import stats
            z_score = stats.norm.ppf((1 + confidence_level) / 2)
        except:
            z_score = 1.96  # 95% confidence
        
        margin = z_score * std
        
        return {
            "upper": (forecast_array + margin).tolist(),
            "lower": (forecast_array - margin).tolist(),
            "confidence_level": confidence_level,
            "margin": float(margin)
        }
    
    @staticmethod
    def calculate_error_metrics(
        actual: List[float],
        predicted: List[float]
    ) -> Dict[str, float]:
        """Calculate error metrics."""
        if len(actual) != len(predicted) or len(actual) == 0:
            return {}
        
        actual_array = np.array(actual)
        predicted_array = np.array(predicted)
        
        mae = np.mean(np.abs(actual_array - predicted_array))
        rmse = np.sqrt(np.mean((actual_array - predicted_array) ** 2))
        
        mask = actual_array != 0
        if mask.any():
            mape = np.mean(np.abs((actual_array[mask] - predicted_array[mask]) / actual_array[mask])) * 100
        else:
            mape = float('inf')
        
        ss_res = np.sum((actual_array - predicted_array) ** 2)
        ss_tot = np.sum((actual_array - np.mean(actual_array)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        accuracy = 1 - (mape / 100) if mape != float('inf') else 0
        
        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape) if mape != float('inf') else None,
            "r2": float(r2),
            "accuracy": float(max(0, min(1, accuracy)))
        }