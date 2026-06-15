import os
import json
from datetime import datetime
from typing import Iterable, Any

from app.ai.arima import train_arima, save_model, load_model


REGISTRY_PATH = "models/registry.json"


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


def train_and_register(series: Iterable[float], order: tuple[int, int, int], name: str | None = None) -> str:
    fitted = train_arima(series, order=order)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    name = name or "arima"
    model_path = f"models/{name}_{ts}.pkl"
    save_model(fitted, model_path)
    metadata = {"order": order, "trained_at": ts}
    register_model(name, model_path, metadata)
    return model_path


def get_latest_model(name: str) -> str | None:
    _ensure_registry()
    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)
    if name not in data or not data[name]:
        return None
    return data[name][-1]["path"]


def load_registered_model(path: str):
    return load_model(path)
