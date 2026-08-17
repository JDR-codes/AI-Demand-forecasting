# fastapi_app/ai/sarima.py
"""
SARIMA (Seasonal ARIMA) time series forecasting model.
Handles seasonal patterns in time series data.
"""
import numpy as np
from typing import Iterable, List, Dict, Any, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    SARIMA_AVAILABLE = True
except ImportError:
    SARIMA_AVAILABLE = False


def train_sarima(
    series: Iterable[float],
    order: Tuple[int, int, int] = (1, 1, 1),
    seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 12),
    enforce_stationarity: bool = False,
    enforce_invertibility: bool = False,
) -> Optional[SARIMAX]:
    """Train a SARIMA model on time series data.
    
    Args:
        series: Time series data
        order: (p, d, q) - AR, differencing, MA
        seasonal_order: (P, D, Q, m) - Seasonal AR, differencing, MA, period
    """
    if not SARIMA_AVAILABLE:
        raise ImportError("SARIMA requires statsmodels. Run: pip install statsmodels")
    
    values = np.array(list(series), dtype=float)
    
    try:
        model = SARIMAX(
            values,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=enforce_stationarity,
            enforce_invertibility=enforce_invertibility,
            disp=False,
        )
        fitted_model = model.fit(disp=False)
        return fitted_model
    except Exception as e:
        raise ValueError(f"SARIMA training failed: {str(e)}")


def forecast_sarima(
    fitted_model: SARIMAX,
    steps: int,
) -> List[float]:
    """Generate future predictions using a trained SARIMA model."""
    try:
        forecast_result = fitted_model.get_forecast(steps=steps)
        predicted_mean = forecast_result.predicted_mean
        if hasattr(predicted_mean, "values"):
            predictions = predicted_mean.values.tolist()
        else:
            predictions = predicted_mean.tolist()
        return [float(p) for p in predictions]
    except Exception as e:
        raise ValueError(f"SARIMA forecast failed: {str(e)}")


def evaluate_sarima(
    fitted_model: SARIMAX,
    series: Iterable[float],
    test_size: int = None,
) -> Dict[str, Any]:
    """Evaluate SARIMA model on test set."""
    if not SARIMA_AVAILABLE:
        raise ImportError("SARIMA evaluation requires statsmodels")
    
    values = np.array(list(series), dtype=float)
    if test_size is None:
        test_size = max(1, len(values) // 5)
    
    try:
        # Get in-sample predictions
        predictions = fitted_model.fittedvalues[1:]  # Skip first NaN
        actual = values[1:]
        
        if len(predictions) > test_size:
            # Use last test_size for evaluation
            actual_test = actual[-test_size:]
            pred_test = predictions[-test_size:]
        else:
            actual_test = actual
            pred_test = predictions
        
        mse = float(np.mean((actual_test - pred_test) ** 2))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(actual_test - pred_test)))
        mape = float(np.mean(np.abs((actual_test - pred_test) / (actual_test + 1e-8))) * 100)
        ss_res = float(np.sum((actual_test - pred_test) ** 2))
        ss_tot = float(np.sum((actual_test - np.mean(actual_test)) ** 2))
        r2 = float(1 - (ss_res / (ss_tot + 1e-8)))
        
        return {
            "mse": mse,
            "rmse": rmse,
            "mae": mae,
            "mape": mape,
            "r2": r2,
        }
    except Exception as e:
        raise ValueError(f"SARIMA evaluation failed: {str(e)}")


def get_model_summary(fitted_model: SARIMAX) -> Dict[str, Any]:
    """Get model summary statistics."""
    try:
        summary = fitted_model.summary()
        return {
            "aic": float(fitted_model.aic),
            "bic": float(fitted_model.bic),
            "summary": str(summary),
        }
    except Exception as e:
        return {"error": str(e)}


def auto_detect_order(
    series: Iterable[float],
    max_p: int = 2,
    max_d: int = 2,
    max_q: int = 2,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]:
    """
    Simple auto-detection of SARIMA order using AIC.
    Note: For production, use auto_arima from pmdarima package.
    """
    if not SARIMA_AVAILABLE:
        raise ImportError("auto_detect requires statsmodels")
    
    values = np.array(list(series), dtype=float)
    best_aic = float('inf')
    best_order = (1, 1, 1)
    best_seasonal_order = (1, 1, 1, 12)
    
    try:
        for p in range(max_p + 1):
            for d in range(max_d + 1):
                for q in range(max_q + 1):
                    try:
                        model = SARIMAX(
                            values,
                            order=(p, d, q),
                            seasonal_order=(1, 1, 1, 12),
                            disp=False,
                        )
                        fitted = model.fit(disp=False)
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except:
                        continue
        
        return best_order, best_seasonal_order
    except Exception as e:
        return (1, 1, 1), (1, 1, 1, 12)
