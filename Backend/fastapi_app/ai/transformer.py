# fastapi_app/ai/transformer.py
"""
Transformer-based time series forecasting model.
Uses multi-head attention for sequence-to-sequence forecasting.
"""
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


class TransformerRegressor(nn.Module):
    """Transformer-based regressor for time series forecasting."""
    
    def __init__(
        self,
        input_size: int = 1,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_embedding = nn.Linear(input_size, d_model)
        self.positional_encoding = self._create_positional_encoding(d_model, max_len=100)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation='relu'
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.output_layer = nn.Linear(d_model, 1)
    
    def _create_positional_encoding(self, d_model, max_len=100):
        """Create positional encoding for transformer."""
        pe = np.zeros((max_len, d_model))
        position = np.arange(0, max_len).reshape(-1, 1)
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)
        return torch.tensor(pe, dtype=torch.float32).unsqueeze(0)
    
    def forward(self, x):
        # x shape: (batch_size, seq_len, 1)
        x = self.input_embedding(x)  # (batch_size, seq_len, d_model)
        
        # Add positional encoding
        if x.size(1) <= self.positional_encoding.size(1):
            x = x + self.positional_encoding[:, :x.size(1), :].to(x.device)
        
        # Transformer encoder
        x = self.transformer_encoder(x)  # (batch_size, seq_len, d_model)
        
        # Take the last output and project to 1D
        x = x[:, -1, :]  # (batch_size, d_model)
        x = self.output_layer(x)  # (batch_size, 1)
        return x.squeeze(-1)


def train_transformer(
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
    epochs: int = 20,
    batch_size: int = 16,
    lr: float = 1e-3,
    d_model: int = 64,
    nhead: int = 4,
    num_layers: int = 2,
) -> TransformerRegressor:
    """Train a Transformer model on time series data."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    if split < 1:
        raise ValueError("Series too short for Transformer training")
    
    X_train, y_train = X[:split], y[:split]
    
    train_loader = DataLoader(
        TensorDataset(
            torch.tensor(X_train[:, :, None], dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32),
        ),
        batch_size=min(batch_size, len(X_train)),
        shuffle=True,
    )
    
    model = TransformerRegressor(
        input_size=1,
        d_model=d_model,
        nhead=nhead,
        num_layers=num_layers,
    )
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


def forecast_transformer(
    model: TransformerRegressor,
    series: Iterable[float],
    steps: int,
    n_lags: int = 7,
) -> List[float]:
    """Generate future predictions using a trained Transformer model."""
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


def evaluate_transformer(
    model: TransformerRegressor,
    series: Iterable[float],
    n_lags: int = 7,
    test_frac: float = 0.2,
) -> Dict[str, Any]:
    """Evaluate Transformer model on test set."""
    X, y = prepare_supervised(series, n_lags=n_lags)
    split = int(len(X) * (1 - test_frac))
    X_test, y_test = X[split:], y[split:]
    
    if len(X_test) == 0:
        raise ValueError("No test data available")
    
    model.eval()
    with torch.no_grad():
        X_test_tensor = torch.tensor(X_test[:, :, None], dtype=torch.float32)
        preds = model(X_test_tensor).numpy()
    
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
