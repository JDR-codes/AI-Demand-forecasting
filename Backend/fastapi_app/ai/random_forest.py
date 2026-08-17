# fastapi_app/ai/random_forest.py
"""
Random Forest time series forecasting model.
Uses ensemble of decision trees for robust predictions.
"""
import numpy as np
from typing import Iterable, Tuple, List, Dict, Any
from sklearn.ensemble import RandomForestRegressor


def prepare_supervised(series: Iterable[float], n_lags: int = 7) -> Tuple[np.ndarray, np.ndarray]:
    """Convert time series into supervised learning format."""
    values = np.array(list(series), dtype=float)
    X, y = [], []
    for i in range(n_lags, len(values)):
        X.append(values[i - n_lags : i])
        y.append(values[i])
    return np.array(X), np.array(y)


def train_random_forest(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
    n_estimators: int = 100,
    max_depth: int = 15,
    min_samples_split: int = 2,
    min_samples_leaf: int = 1,
    random_state: int = 42,
) -> RandomForestRegressor:
    """Train a Random Forest model on time series data."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    if split < 1:
        raise ValueError("Series too short for Random Forest training")
    
    X_train, y_train = X[:split], y[:split]
    
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model


def forecast_random_forest(
    model: RandomForestRegressor,
    series: Iterable[float],
    steps: int,
    n_lags: int = 7,
) -> List[float]:
    """Generate future predictions using a trained Random Forest model."""
    values = np.array(list(series), dtype=float)
    window = values[-n_lags:].tolist()
    predictions = []
    
    for _ in range(steps):
        pred_value = float(model.predict(np.array([window]))[0])
        predictions.append(pred_value)
        window = window[1:] + [pred_value]
    
    return predictions


def evaluate_random_forest(
    model: RandomForestRegressor,
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
) -> Dict[str, Any]:
    """Evaluate Random Forest model on test set."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    X_test, y_test = X[split:], y[split:]
    
    if len(X_test) == 0:
        raise ValueError("No test data available")
    
    preds = model.predict(X_test)
    
    mse = float(np.mean((y_test - preds) ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(y_test - preds)))
    mape = float(np.mean(np.abs((y_test - preds) / (y_test + 1e-8))) * 100)
    ss_res = float(np.sum((y_test - preds) ** 2))
    ss_tot = float(np.sum((y_test - np.mean(y_test)) ** 2))
    r2 = float(1 - (ss_res / (ss_tot + 1e-8)))
    
    return {
        "mse": mse,
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
        "r2": r2,
    }


def get_feature_importance(model: RandomForestRegressor, n_lags: int = 7) -> Dict[str, float]:
    """Get feature importance from trained model."""
    importance = model.feature_importances_
    importance_dict = {}
    for i, imp in enumerate(importance):
        importance_dict[f"lag_{i+1}"] = float(imp)
    return importance_dict
