#fastapi_app/ai/arima.py
import pandas as pd
import joblib
from statsmodels.tsa.arima.model import ARIMA
from typing import Iterable, List, Any
import numpy as np


def train_arima(series: Iterable[float], order: tuple[int, int, int] = (1, 1, 1)) -> Any:
    """Train a simple ARIMA model on a 1-D numeric series and return the fitted model."""
    s = pd.Series(list(series))
    if not isinstance(s.index, pd.DatetimeIndex):
        s.index = pd.date_range(start="2020-01-01", periods=len(s), freq="D")
    model = ARIMA(s, order=order)
    fitted = model.fit()
    return fitted


def forecast(fitted_model: Any, steps: int) -> List[float]:
    """Produce a forecast for `steps` future points."""
    preds = fitted_model.forecast(steps=steps)
    return [float(x) for x in preds]


# ✅ REMOVE calculate_metrics - now in forecast_metrics.py
# The ForecastMetricsService.calculate_error_metrics() should be used instead


def find_peaks(values: Iterable[float], top_n: int = 3) -> List[dict[str, float]]:
    """Return the top N peak values from a numerical series."""
    values_arr = np.array(list(values), dtype=float)
    if values_arr.size == 0:
        return []
    top_n = min(top_n, len(values_arr))
    peak_indices = np.argsort(values_arr)[-top_n:][::-1]
    return [
        {"step": int(idx + 1), "value": float(values_arr[idx])}
        for idx in peak_indices
    ]


def save_model(fitted_model: Any, path: str) -> None:
    """Save fitted model to disk using joblib."""
    joblib.dump(fitted_model, path)


def load_model(path: str) -> Any:
    """Load a fitted model from disk."""
    return joblib.load(path)