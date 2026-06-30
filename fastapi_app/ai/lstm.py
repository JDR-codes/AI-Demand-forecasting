import numpy as np
from typing import Iterable, Tuple, List, Dict, Any
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


def prepare_supervised(series: Iterable[float], n_lags: int = 7) -> Tuple[np.ndarray, np.ndarray]:
    """Convert time series into supervised learning format."""
    values = np.array(list(series), dtype=float)
    X, y = [], []
    for i in range(n_lags, len(values)):
        X.append(values[i - n_lags : i])
        y.append(values[i])
    return np.array(X), np.array(y)


class LSTMRegressor(nn.Module):
    """LSTM-based regressor for time series forecasting."""
    
    def __init__(self, input_size: int = 1, hidden_size: int = 32, num_layers: int = 1, dropout: float = 0.0):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0.0)
        self.linear = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1:, :]
        return self.linear(out).squeeze(-1)


def train_lstm(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
    epochs: int = 20,
    batch_size: int = 16,
    lr: float = 1e-3,
    hidden_size: int = 32,
    num_layers: int = 1,
) -> LSTMRegressor:
    """Train an LSTM model on time series data."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    if split < 1:
        raise ValueError("Series too short for LSTM training")
    
    X_train, y_train = X[:split], y[:split]
    
    train_loader = DataLoader(
        TensorDataset(
            torch.tensor(X_train[:, :, None], dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32),
        ),
        batch_size=min(batch_size, len(X_train)),
        shuffle=True,
    )
    
    model = LSTMRegressor(input_size=1, hidden_size=hidden_size, num_layers=num_layers)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    
    model.train()
    for _ in range(epochs):
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = loss_fn(preds, batch_y)
            loss.backward()
            optimizer.step()
    
    return model


def forecast_lstm(
    model: LSTMRegressor,
    series: Iterable[float],
    steps: int,
    n_lags: int = 7,
) -> List[float]:
    """Generate future predictions using a trained LSTM model."""
    values = np.array(list(series), dtype=float)
    window = values[-n_lags:].tolist()
    predictions = []
    
    model.eval()
    with torch.no_grad():
        for _ in range(steps):
            window_tensor = torch.tensor([window], dtype=torch.float32).unsqueeze(-1)
            pred_value = float(model(window_tensor).numpy().flatten()[0])
            predictions.append(pred_value)
            window = window[1:] + [pred_value]
    
    return predictions


def evaluate_lstm(
    model: LSTMRegressor,
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
) -> Dict[str, Any]:
    """Evaluate LSTM model on test set."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    X_test, y_test = X[split:], y[split:]
    
    if len(X_test) == 0:
        raise ValueError("No test data available")
    
    model.eval()
    with torch.no_grad():
        X_test_tensor = torch.tensor(X_test[:, :, None], dtype=torch.float32)
        preds = model(X_test_tensor).numpy().flatten()
    
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
