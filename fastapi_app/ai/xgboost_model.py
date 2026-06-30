import numpy as np
from typing import Iterable, Tuple, List, Dict, Any
from xgboost import XGBRegressor


def prepare_supervised(series: Iterable[float], n_lags: int = 7) -> Tuple[np.ndarray, np.ndarray]:
    """Convert time series into supervised learning format."""
    values = np.array(list(series), dtype=float)
    X, y = [], []
    for i in range(n_lags, len(values)):
        X.append(values[i - n_lags : i])
        y.append(values[i])
    return np.array(X), np.array(y)


def train_xgboost(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
    n_estimators: int = 100,
    learning_rate: float = 0.1,
    max_depth: int = 6,
) -> XGBRegressor:
    """Train an XGBoost model on time series data."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    if split < 1:
        raise ValueError("Series too short for XGBoost training")
    
    X_train, y_train = X[:split], y[:split]
    
    model = XGBRegressor(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        objective="reg:squarederror",
        verbosity=0,
    )
    model.fit(X_train, y_train)
    return model


def forecast_xgboost(model: XGBRegressor, series: Iterable[float], steps: int, n_lags: int = 7) -> List[float]:
    """Generate future predictions using a trained XGBoost model."""
    values = np.array(list(series), dtype=float)
    window = values[-n_lags:].tolist()
    predictions = []
    
    for _ in range(steps):
        pred_value = float(model.predict(np.array([window]))[0])
        predictions.append(pred_value)
        window = window[1:] + [pred_value]
    
    return predictions


def evaluate_xgboost(
    model: XGBRegressor,
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
) -> Dict[str, Any]:
    """Evaluate XGBoost model on test set."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    X_test, y_test = X[split:], y[split:]
    
    if len(X_test) == 0:
        raise ValueError("No test data available")
    
    preds = model.predict(X_test)
    mse = float(np.mean((y_test - preds) ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(y_test - preds)))
    
    return {
        "mse": mse,
        "rmse": rmse,
        "mae": mae,
        "test_predictions": preds.tolist(),
        "test_actuals": y_test.tolist(),
    }
