from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Tuple
import os

from fastapi_app.ai.arima import forecast as arima_forecast
from fastapi_app.services.forecast.forecast_service import train_and_register, get_latest_model, load_registered_model


class TrainRequest(BaseModel):
    series: list[float]
    order: Tuple[int, int, int] = (1, 1, 1)
    name: str | None = None


class ForecastRequest(BaseModel):
    steps: int
    model_path: str | None = None
    name: str | None = None


router = APIRouter(prefix="/api/forecast")


@router.post("/train")
def train(req: TrainRequest):
    if not req.series:
        raise HTTPException(status_code=400, detail="Series is empty")
    model_path = train_and_register(req.series, order=tuple(req.order), name=req.name)
    return {"message": "model_trained", "model_path": model_path}


@router.post("/predict")
def predict(req: ForecastRequest):
    if req.steps <= 0:
        raise HTTPException(status_code=400, detail="steps must be > 0")
    model_path = req.model_path
    if not model_path and req.name:
        model_path = get_latest_model(req.name)
    if not model_path or not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="model not found")
    model = load_registered_model(model_path)
    preds = arima_forecast(model, req.steps)
    return {"predictions": preds, "model_path": model_path}
