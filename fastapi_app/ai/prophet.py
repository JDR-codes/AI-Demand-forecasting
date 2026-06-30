import os
import numpy as np
from typing import Iterable, List, Dict, Any
import pandas as pd

try:
    from prophet import Prophet
except ImportError:
    Prophet = None


def train_prophet(
    series: Iterable[float],
    date_index: pd.DatetimeIndex | None = None,
    test_frac: float = 0.2,
    yearly_seasonality: bool = True,
    weekly_seasonality: bool = True,
) -> tuple:
    if Prophet is None:
        raise ImportError("Prophet not installed. Run: pip install prophet")

    values = np.array(list(series), dtype=float)
    dates = date_index if date_index is not None else pd.date_range(
        start="2020-01-01", periods=len(values), freq="D"
    )

    df = pd.DataFrame({"ds": dates, "y": values})
    split = int(len(df) * (1 - test_frac))
    train_df = df[:split].copy()
    test_df = df[split:].copy()

    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        daily_seasonality=False,
        interval_width=0.95,
    )

    # Suppress Prophet's verbose stdout
    import sys
    with open(os.devnull, "w") as devnull:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            model.fit(train_df)
        except Exception as e:
            raise RuntimeError(
                f"Prophet fitting failed — this is likely a Python version issue. "
                f"Prophet requires Python 3.9–3.11. You are on {sys.version}. "
                f"Original error: {e}"
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    return model, train_df, test_df


def forecast_prophet(model, periods: int) -> List[float]:
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    return forecast["yhat"].tail(periods).tolist()


def evaluate_prophet(model, test_df: pd.DataFrame) -> Dict[str, Any]:
    future_test = pd.DataFrame({"ds": test_df["ds"].values})
    forecast_test = model.predict(future_test)

    preds = forecast_test["yhat"].values
    actuals = test_df["y"].values

    mse = float(np.mean((actuals - preds) ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(actuals - preds)))
    mape = float(np.mean(np.abs((actuals - preds) / np.where(actuals == 0, 1, actuals))) * 100)

    return {
        "mse": mse,
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
        "test_predictions": preds.tolist(),
        "test_actuals": actuals.tolist(),
    }