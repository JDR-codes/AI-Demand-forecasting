import pandas as pd
import joblib
from statsmodels.tsa.arima.model import ARIMA
from typing import Iterable, List, Any


def train_arima(series: Iterable[float], order: tuple[int, int, int] = (1, 1, 1)) -> Any:
    """Train a simple ARIMA model on a 1-D numeric series and return the fitted model."""
    s = pd.Series(list(series))
    model = ARIMA(s, order=order)
    fitted = model.fit()
    return fitted


def forecast(fitted_model: Any, steps: int) -> List[float]:
    """Produce a forecast for `steps` future points."""
    preds = fitted_model.forecast(steps=steps)
    return [float(x) for x in preds]


def save_model(fitted_model: Any, path: str) -> None:
    """Save fitted model to disk using joblib."""
    joblib.dump(fitted_model, path)


def load_model(path: str) -> Any:
    """Load a fitted model from disk."""
    return joblib.load(path)
import pandas as pd
import joblib
from statsmodels.tsa.arima.model import ARIMA
from typing import Iterable, List, Any


def train_arima(series: Iterable[float], order: tuple[int, int, int] = (1, 1, 1)) -> Any:
    """Train a simple ARIMA model on a 1-D numeric series and return the fitted model."""
    s = pd.Series(list(series))
    model = ARIMA(s, order=order)
    fitted = model.fit()
    return fitted


def forecast(fitted_model: Any, steps: int) -> List[float]:
    """Produce a forecast for `steps` future points."""
    preds = fitted_model.forecast(steps=steps)
    return [float(x) for x in preds]


def save_model(fitted_model: Any, path: str) -> None:
    """Save fitted model to disk using joblib."""
    joblib.dump(fitted_model, path)


def load_model(path: str) -> Any:
    """Load a fitted model from disk."""
    return joblib.load(path)
