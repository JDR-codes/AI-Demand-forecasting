from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Literal
import os

from fastapi_app.ai.arima import (
    forecast as arima_forecast,
    find_peaks,
)
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.models.auth_model import User
from fastapi_app.services.forecast.forecast_service import (
    train_and_register,
    load_registered_model,
    prepare_series,
    train_xgboost,
    train_lstm,
    train_prophet,
)


class TrainModelRequest(BaseModel):
    model_type: Literal["arima", "xgboost", "lstm", "prophet"]
    csv_path: str | None = None
    actuals: list[float] | None = None
    steps: int = 7
    order: tuple[int, int, int] = (1, 1, 1)


class PredictWithModelRequest(BaseModel):
    model_type: Literal["arima", "xgboost", "lstm", "prophet"]
    steps: int = 7
    actuals: list[float] | None = None
    csv_path: str | None = None


router = APIRouter(prefix="/api/forecast")


@router.post("/train-model")
def train_model(
    req: TrainModelRequest,
    current_user: User = Depends(get_current_user),
):
    """Train the selected model on cleaned data and return training metrics."""
    if not req.csv_path and not req.actuals:
        raise HTTPException(status_code=400, detail="Provide either csv_path or actuals for training")

    try:
        training_values = prepare_series(path=req.csv_path) if req.csv_path else req.actuals
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    training_values = training_values.tolist() if hasattr(training_values, "tolist") else training_values

    if req.model_type == "arima":
        model_path = train_and_register(
            training_values,
            order=req.order,
            name="trained_arima",
            model_type="arima",
        )
        model = load_registered_model(model_path)
        preds = arima_forecast(model, req.steps)
        response = {
            "model_type": "arima",
            "model_path": model_path,
            "metrics": {
                "aic": float(getattr(model, "aic", 0)),
                "bic": float(getattr(model, "bic", 0)),
                "hqic": float(getattr(model, "hqic", 0)),
            },
            "forecast": preds,
            "peaks": find_peaks(preds, top_n=3),
        }
    elif req.model_type == "xgboost":
        results = train_xgboost(training_values)
        response = {
            "model_type": "xgboost",
            "metrics": results["metrics"],
            "forecast": results["future_predictions"],
            "peaks": results["peaks"],
        }
    elif req.model_type == "lstm":
        results = train_lstm(training_values)
        response = {
            "model_type": "lstm",
            "metrics": results["metrics"],
            "forecast": results["future_predictions"],
            "peaks": results["peaks"],
        }
    else:
        results = train_prophet(training_values)
        if results.get("error"):
            raise HTTPException(status_code=400, detail=results["error"])
        response = {
            "model_type": "prophet",
            "metrics": results["metrics"],
            "forecast": results["future_predictions"],
            "peaks": results["peaks"],
        }

    return response


@router.post("/compare-models")
def compare_models(
    csv_path: str = Query(None, description="Path to CSV file"),
    current_user: User = Depends(get_current_user),
):
    """Train all 4 models and compare their metrics.
    
    Returns metrics for ARIMA, XGBoost, LSTM, and Prophet models
    so you can select the best one for predictions.
    """
    try:
        training_values = prepare_series(path=csv_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        # Train ARIMA
        arima_path = train_and_register(
            training_values.tolist(), 
            order=(1, 1, 1), 
            name="compare_arima", 
            model_type="arima"
        )
        arima_model = load_registered_model(arima_path)
        arima_future = arima_forecast(arima_model, 7)

        # Train XGBoost
        xgb_results = train_xgboost(training_values, n_lags=7)

        # Train LSTM
        lstm_results = train_lstm(training_values, n_lags=7)

        # Train Prophet
        prophet_results = train_prophet(training_values)

        return {
            "comparison": {
                "arima": {
                    "model_type": "arima",
                    "metrics": {
                        "aic": float(getattr(arima_model, "aic", 0)),
                        "bic": float(getattr(arima_model, "bic", 0)),
                        "hqic": float(getattr(arima_model, "hqic", 0)),
                    },
                    "forecast_sample": arima_future[:3],
                    "peaks": find_peaks(arima_future, top_n=3),
                },
                "xgboost": {
                    "model_type": "xgboost",
                    "metrics": xgb_results["metrics"],
                    "forecast_sample": xgb_results["future_predictions"][:3],
                    "peaks": xgb_results["peaks"],
                },
                "lstm": {
                    "model_type": "lstm",
                    "metrics": lstm_results["metrics"],
                    "forecast_sample": lstm_results["future_predictions"][:3],
                    "peaks": lstm_results["peaks"],
                },
                "prophet": {
                    "model_type": "prophet",
                    "metrics": prophet_results.get("metrics", {}),
                    "forecast_sample": prophet_results.get("future_predictions", [])[:3],
                    "peaks": prophet_results.get("peaks", []),
                    "error": prophet_results.get("error"),
                },
            },
            "recommendation": "Select the model with the lowest RMSE/MSE for best accuracy",
            "dataset": csv_path or "default",
            "training_length": len(training_values),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(exc)}")


@router.post("/predict-with-model")
def predict_with_model(
    req: PredictWithModelRequest,
    current_user: User = Depends(get_current_user),
):
    """Train a specific model and return predictions with metrics.
    
    Select from: arima, xgboost, lstm, prophet
    Provide either csv_path or actuals for training.
    """
    try:
        # Load or get training values from CSV or actuals
        if req.csv_path:
            training_values = prepare_series(path=req.csv_path)
        elif req.actuals:
            training_values = req.actuals
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either csv_path or actuals"
            )
        
        if hasattr(training_values, "tolist"):
            training_values = training_values.tolist()
        
        # Train selected model
        if req.model_type == "arima":
            model_path = train_and_register(
                training_values,
                order=(1, 1, 1),
                name=f"selected_arima",
                model_type="arima"
            )
            model = load_registered_model(model_path)
            preds = arima_forecast(model, req.steps)
            
            response = {
                "model_type": req.model_type,
                "predictions": preds,
                "metrics": {
                    "aic": float(getattr(model, "aic", 0)),
                    "bic": float(getattr(model, "bic", 0)),
                },
                "peaks": find_peaks(preds, top_n=3),
            }
        
        elif req.model_type == "xgboost":
            results = train_xgboost(training_values)
            response = {
                "model_type": req.model_type,
                "predictions": results["future_predictions"],
                "metrics": results["metrics"],
                "peaks": results["peaks"],
            }
        
        elif req.model_type == "lstm":
            results = train_lstm(training_values)
            response = {
                "model_type": req.model_type,
                "predictions": results["future_predictions"],
                "metrics": results["metrics"],
                "peaks": results["peaks"],
            }
        
        elif req.model_type == "prophet":
            results = train_prophet(training_values)
            if results.get("error"):
                raise HTTPException(status_code=400, detail=results["error"])
            response = {
                "model_type": req.model_type,
                "predictions": results["future_predictions"],
                "metrics": results["metrics"],
                "peaks": results["peaks"],
            }
        
        # Add actuals for metric comparison if provided
        if req.actuals:
            response["actuals_provided"] = True
        
        return response
    
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(exc)}"
        )
