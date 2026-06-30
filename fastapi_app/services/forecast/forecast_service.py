import os
import json
from datetime import datetime
from typing import Iterable, Any, Tuple

import numpy as np
import pandas as pd

from fastapi_app.ai.arima import (
    train_arima,
    save_model,
    load_model,
    calculate_metrics,
    find_peaks,
    forecast as arima_forecast,
)
from fastapi_app.ai.xgboost_model import (
    train_xgboost as xgb_train,
    forecast_xgboost as xgb_forecast,
    evaluate_xgboost as xgb_evaluate,
)
from fastapi_app.ai.lstm import (
    train_lstm as lstm_train,
    forecast_lstm as lstm_forecast,
    evaluate_lstm as lstm_evaluate,
)
from fastapi_app.ai.prophet import (
    train_prophet as prophet_train,
    forecast_prophet as prophet_forecast,
    evaluate_prophet as prophet_evaluate,
)
from fastapi_app.core.config import BASE_DIR, DATA_DIR, DEFAULT_DATASET_PATH, REGISTRY_PATH, MODELS_DIR, UPLOADS_DIR


def _ensure_registry():
    dirpath = os.path.dirname(REGISTRY_PATH)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    if not os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "w") as f:
            json.dump({}, f)


def register_model(name: str, model_path: str, metadata: dict) -> None:
    _ensure_registry()
    with open(REGISTRY_PATH, "r+") as f:
        data = json.load(f)
        if name not in data:
            data[name] = []
        data[name].append({"path": model_path, "metadata": metadata})
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


def train_and_register(series: Iterable[float], order: tuple[int, int, int], name: str | None = None, model_type: str = "arima") -> str:
    fitted = train_arima(series, order=order)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    name = name or "arima"
    model_path = os.path.join(MODELS_DIR, f"{name}_{ts}.pkl")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    save_model(fitted, model_path)
    metadata = {"order": order, "trained_at": ts, "type": model_type}
    register_model(name, model_path, metadata)
    return model_path


def get_registered_models() -> dict:
    _ensure_registry()
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def get_latest_model(name: str) -> str | None:
    _ensure_registry()
    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)
    if name not in data or not data[name]:
        return None
    return data[name][-1]["path"]


def load_registered_model(path: str):
    return load_model(path)


def prepare_series(path: str | None = None, date_col: str = "Date", value_col: str = "Demand", resample_rule: str = "D") -> pd.Series:
    requested_path = path or DEFAULT_DATASET_PATH
    dataset_path = requested_path

    if not os.path.isabs(dataset_path):
        candidates = [
            dataset_path,
            os.path.join(BASE_DIR, dataset_path),
            os.path.join(DATA_DIR, dataset_path),
            os.path.join(UPLOADS_DIR, dataset_path),
        ]
        dataset_path = next((p for p in candidates if os.path.isfile(p)), requested_path)

    if not os.path.isfile(dataset_path):
        raise FileNotFoundError(f"Dataset file not found: {requested_path}")

    df = pd.read_csv(dataset_path, parse_dates=[date_col])
    df = df.set_index(date_col)
    series = df[value_col].astype(float).resample(resample_rule).sum()
    series = series.interpolate().bfill().ffill()
    return series


def train_xgboost(series: Iterable[float], n_lags: int = 7, test_frac: float = 0.2) -> dict:
    model = xgb_train(series, n_lags=n_lags, test_frac=test_frac)
    metrics = xgb_evaluate(model, series, n_lags=n_lags, test_frac=test_frac)
    preds = metrics.pop("test_predictions")
    
    future_preds = xgb_forecast(model, series, steps=7, n_lags=n_lags)
    
    return {
        "model_type": "xgboost",
        "metrics": {k: v for k, v in metrics.items() if k != "test_actuals"},
        "test_predictions": preds,
        "future_predictions": future_preds,
        "peaks": find_peaks(preds, top_n=3),
    }


def train_lstm(series: Iterable[float], n_lags: int = 7, test_frac: float = 0.2, epochs: int = 20, batch_size: int = 16) -> dict:
    model = lstm_train(series, n_lags=n_lags, test_frac=test_frac, epochs=epochs, batch_size=batch_size)
    metrics = lstm_evaluate(model, series, n_lags=n_lags, test_frac=test_frac)
    preds = metrics.pop("test_predictions")
    
    future_preds = lstm_forecast(model, series, steps=7, n_lags=n_lags)
    
    return {
        "model_type": "lstm",
        "metrics": {k: v for k, v in metrics.items() if k != "test_actuals"},
        "test_predictions": preds,
        "future_predictions": future_preds,
        "peaks": find_peaks(preds, top_n=3),
    }


def train_prophet(series: Iterable[float], test_frac: float = 0.2) -> dict:
    try:
        model, train_df, test_df = prophet_train(series, test_frac=test_frac)
        metrics = prophet_evaluate(model, test_df)
        preds = metrics.pop("test_predictions")
        
        future_preds = prophet_forecast(model, periods=7)
        
        return {
            "model_type": "prophet",
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
    except RuntimeError as exc:
        return {
            "model_type": "prophet",
            "error": f"Prophet training failed: {str(exc)}",
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


def auto_forecast_report(path: str | None = None, forecast_steps: int = 7) -> dict[str, Any]:
    series = prepare_series(path)
    arima_path = train_and_register(series.tolist(), order=(1, 1, 1), name="auto_arima", model_type="arima")
    arima_model = load_registered_model(arima_path)
    arima_future = arima_forecast(arima_model, forecast_steps)

    xgboost_report = train_xgboost(series, n_lags=7)
    lstm_report = train_lstm(series, n_lags=7)
    prophet_report = train_prophet(series)

    return {
        "dataset": path or DEFAULT_DATA_PATH,
        "series_length": len(series),
        "arima": {
            "model_path": arima_path,
            "forecast": arima_future,
            "peaks": find_peaks(arima_future, top_n=3),
            "model_stats": {
                "aic": getattr(arima_model, "aic", None),
                "bic": getattr(arima_model, "bic", None),
                "hqic": getattr(arima_model, "hqic", None),
                "sigma2": float(getattr(arima_model, "sigma2", 0.0)),
            },
        },
        "xgboost": xgboost_report,
        "lstm": lstm_report,
        "prophet": prophet_report,
        "registered_models": get_registered_models(),
    }
