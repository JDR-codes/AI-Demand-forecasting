#fastapi_app/services/forecast/forecast_service.py

"""
Pure ML algorithms and model management.
No business logic, no job management, no reporting.
"""
import os
import json
import pickle
from datetime import datetime
from typing import Iterable, Any, Tuple, List, Optional, Dict
import pandas as pd
import numpy as np

from fastapi_app.core.config import BASE_DIR, DATA_DIR, DEFAULT_DATASET_PATH, REGISTRY_PATH, MODELS_DIR
# ============================================================================
# MODEL REGISTRY HELPERS
# ============================================================================

def _ensure_registry():
    dirpath = os.path.dirname(REGISTRY_PATH)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    if not os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "w") as f:
            json.dump({}, f)


def register_model(name: str, model_path: str, metadata: dict) -> None:
    """Register a trained model in the registry."""
    _ensure_registry()
    with open(REGISTRY_PATH, "r+") as f:
        data = json.load(f)
        if name not in data:
            data[name] = []
        data[name].append({"path": model_path, "metadata": metadata})
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


def get_registered_models() -> dict:
    """Get all registered models."""
    _ensure_registry()
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def get_latest_model(name: str) -> str | None:
    """Get the latest model path for a given name."""
    _ensure_registry()
    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)
    if name not in data or not data[name]:
        return None
    return data[name][-1]["path"]


def load_registered_model(path: str):
    """Load a model from disk."""
    from fastapi_app.ai.arima import load_model
    return load_model(path)


# ============================================================================
# TRAINING FUNCTIONS
# ============================================================================

def train_and_register(
    series: Iterable[float],
    order: tuple[int, int, int] = (1, 1, 1),
    name: str | None = None,
    model_type: str = "arima"
) -> str:
    """Train ARIMA model and register it."""
    from fastapi_app.ai.arima import train_arima, save_model
    fitted = train_arima(series, order=order)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    name = name or "arima"
    model_path = os.path.join(MODELS_DIR, f"{name}_{ts}.pkl")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    save_model(fitted, model_path)
    metadata = {"order": order, "trained_at": ts, "type": model_type}
    register_model(name, model_path, metadata)
    return model_path


def train_xgboost(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2
) -> dict:
    """Train XGBoost model and return results."""
    from fastapi_app.ai.xgboost_model import (
        train_xgboost as xgb_train,
        forecast_xgboost as xgb_forecast,
        evaluate_xgboost as xgb_evaluate,
    )
    from fastapi_app.ai.arima import find_peaks
    model = xgb_train(series, n_lags=n_lags, test_frac=test_frac)
    metrics = xgb_evaluate(model, series, n_lags=n_lags, test_frac=test_frac)
    preds = metrics.pop("test_predictions")
    
    future_preds = xgb_forecast(model, series, steps=7, n_lags=n_lags)
    
    return {
        "model_type": "xgboost",
        "model": model,
        "metrics": {k: v for k, v in metrics.items() if k != "test_actuals"},
        "test_predictions": preds,
        "future_predictions": future_preds,
        "peaks": find_peaks(preds, top_n=3),
    }


def train_lstm(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
    epochs: int = 20,
    batch_size: int = 16
) -> dict:
    """Train LSTM model and return results."""
    from fastapi_app.ai.lstm import (
        train_lstm as lstm_train,
        forecast_lstm as lstm_forecast,
        evaluate_lstm as lstm_evaluate,
    )
    from fastapi_app.ai.arima import find_peaks
    model = lstm_train(series, n_lags=n_lags, test_frac=test_frac, epochs=epochs, batch_size=batch_size)
    metrics = lstm_evaluate(model, series, n_lags=n_lags, test_frac=test_frac)
    preds = metrics.pop("test_predictions")
    
    future_preds = lstm_forecast(model, series, steps=7, n_lags=n_lags)
    
    return {
        "model_type": "lstm",
        "model": model,
        "metrics": {k: v for k, v in metrics.items() if k != "test_actuals"},
        "test_predictions": preds,
        "future_predictions": future_preds,
        "peaks": find_peaks(preds, top_n=3),
    }


def train_prophet(
    series: Iterable[float],
    test_frac: float = 0.2
) -> dict:
    """Train Prophet model and return results."""
    try:
        from fastapi_app.ai.prophet import (
            train_prophet as prophet_train,
            forecast_prophet as prophet_forecast,
            evaluate_prophet as prophet_evaluate,
        )
        from fastapi_app.ai.arima import find_peaks
        model, train_df, test_df = prophet_train(series, test_frac=test_frac)
        metrics = prophet_evaluate(model, test_df)
        preds = metrics.pop("test_predictions")
        
        future_preds = prophet_forecast(model, periods=7)
        
        return {
            "model_type": "prophet",
            "model": model,
            "metrics": {k: v for k, v in metrics.items() if k != "test_actuals"},
            "test_predictions": preds,
            "future_predictions": future_preds,
            "peaks": find_peaks(preds, top_n=3),
        }
    except ImportError:
        return {
            "model_type": "prophet",
            "error": "Prophet not installed. Install with: pip install prophet",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }
    except Exception as exc:
        return {
            "model_type": "prophet",
            "error": f"Prophet training failed: {str(exc)}",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }


def train_transformer(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
    epochs: int = 20,
    batch_size: int = 16
) -> dict:
    """Train Transformer model and return results."""
    try:
        from fastapi_app.ai.transformer import (
            train_transformer as transformer_train,
            forecast_transformer as transformer_forecast,
            evaluate_transformer as transformer_evaluate,
        )
        from fastapi_app.ai.arima import find_peaks
        model = transformer_train(series, n_lags=n_lags, test_frac=test_frac, epochs=epochs, batch_size=batch_size)
        metrics = transformer_evaluate(model, series, n_lags=n_lags, test_frac=test_frac)
        preds = metrics.pop("test_predictions", [])
        
        future_preds = transformer_forecast(model, series, steps=7, n_lags=n_lags)
        
        return {
            "model_type": "transformer",
            "model": model,
            "metrics": metrics,
            "test_predictions": preds,
            "future_predictions": future_preds,
            "peaks": find_peaks(future_preds, top_n=3),
        }
    except ImportError:
        return {
            "model_type": "transformer",
            "error": "PyTorch not installed. Install with: pip install torch",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }
    except Exception as exc:
        return {
            "model_type": "transformer",
            "error": f"Transformer training failed: {str(exc)}",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }


def train_random_forest(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
    n_estimators: int = 100,
) -> dict:
    """Train Random Forest model and return results."""
    try:
        from fastapi_app.ai.random_forest import (
            train_random_forest as rf_train,
            forecast_random_forest as rf_forecast,
            evaluate_random_forest as rf_evaluate,
        )
        from fastapi_app.ai.arima import find_peaks
        model = rf_train(series, n_lags=n_lags, test_frac=test_frac, n_estimators=n_estimators)
        metrics = rf_evaluate(model, series, n_lags=n_lags, test_frac=test_frac)
        preds = metrics.pop("test_predictions", [])
        
        future_preds = rf_forecast(model, series, steps=7, n_lags=n_lags)
        
        return {
            "model_type": "random_forest",
            "model": model,
            "metrics": metrics,
            "test_predictions": preds,
            "future_predictions": future_preds,
            "peaks": find_peaks(future_preds, top_n=3),
        }
    except ImportError:
        return {
            "model_type": "random_forest",
            "error": "scikit-learn not installed. Install with: pip install scikit-learn",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }
    except Exception as exc:
        return {
            "model_type": "random_forest",
            "error": f"Random Forest training failed: {str(exc)}",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }


def train_sarima(
    series: Iterable[float],
    order: Tuple[int, int, int] = (1, 1, 1),
    seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 12),
) -> dict:
    """Train SARIMA model and return results."""
    try:
        from fastapi_app.ai.sarima import (
            train_sarima as sarima_train,
            forecast_sarima as sarima_forecast,
            evaluate_sarima as sarima_evaluate,
        )
        from fastapi_app.ai.arima import find_peaks
        model = sarima_train(series, order=order, seasonal_order=seasonal_order)
        metrics = sarima_evaluate(model, series)
        preds = metrics.pop("test_predictions", [])
        
        future_preds = sarima_forecast(model, steps=7)
        
        return {
            "model_type": "sarima",
            "model": model,
            "metrics": metrics,
            "test_predictions": preds,
            "future_predictions": future_preds,
            "peaks": find_peaks(future_preds, top_n=3),
        }
    except ImportError:
        return {
            "model_type": "sarima",
            "error": "statsmodels not installed. Install with: pip install statsmodels",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }
    except Exception as exc:
        return {
            "model_type": "sarima",
            "error": f"SARIMA training failed: {str(exc)}",
            "metrics": {},
            "test_predictions": [],
            "future_predictions": [],
            "peaks": [],
        }


# ============================================================================
# DATA PREPARATION
# ============================================================================

def prepare_series(
    path: str | None = None,
    date_col: str = "Date",
    value_col: str = "Demand",
    resample_rule: str = "D"
) -> pd.Series:
    """Load and prepare time series data from CSV."""
    requested_path = path or DEFAULT_DATASET_PATH
    dataset_path = requested_path

    if not os.path.isabs(dataset_path):
        candidates = [
            dataset_path,
            os.path.join(BASE_DIR, dataset_path),
            os.path.join(DATA_DIR, dataset_path),
        ]
        dataset_path = next(
            (candidate for candidate in candidates if os.path.isfile(candidate)),
            dataset_path,
        )

    if not os.path.isfile(dataset_path):
        raise FileNotFoundError(f"Dataset file not found: {requested_path}")

    df = pd.read_csv(dataset_path)
    
    # Resolve column names case-insensitively
    actual_date_col = next((c for c in df.columns if c.lower() == date_col.lower()), date_col)
    actual_value_col = next((c for c in df.columns if c.lower() == value_col.lower()), value_col)
    
    df[actual_date_col] = pd.to_datetime(df[actual_date_col])
    df = df.set_index(actual_date_col)
    
    series = df[actual_value_col].astype(float).resample(resample_rule).sum()
    series = series.interpolate().bfill().ffill()
    return series