from datetime import datetime
from typing import Any, Dict, List, Optional
import traceback

from sqlalchemy.orm import Session

from fastapi_app.ai.arima import forecast as arima_forecast
from fastapi_app.models.scenario_model import Scenario
from fastapi_app.schemas.scenario_schema import ScenarioCreate, ScenarioUpdate
from fastapi_app.services.forecast.forecast_service import (
    auto_forecast_report,
    load_registered_model,
    prepare_series,
    train_and_register,
    train_lstm,
    train_prophet,
    train_xgboost,
)
from fastapi_app.services.recommendation.recommendation_service import recommend_from_series


class ScenarioService:
    @staticmethod
    def get_all_scenarios(db: Session) -> List[Scenario]:
        return db.query(Scenario).order_by(Scenario.created_at.desc()).all()

    @staticmethod
    def get_scenario_by_id(db: Session, scenario_id: int) -> Optional[Scenario]:
        return db.query(Scenario).filter(Scenario.id == scenario_id).first()

    @staticmethod
    def create_scenario(db: Session, scenario_create: ScenarioCreate) -> Scenario:
        scenario = Scenario(**scenario_create.dict())
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario

    @staticmethod
    def update_scenario(db: Session, scenario_id: int, scenario_update: ScenarioUpdate) -> Optional[Scenario]:
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return None

        update_data = scenario_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(scenario, key, value)

        scenario.updated_at = datetime.utcnow()
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario

    @staticmethod
    def delete_scenario(db: Session, scenario_id: int) -> bool:
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return False

        db.delete(scenario)
        db.commit()
        return True

    @staticmethod
    def run_scenario(db: Session, scenario_id: int) -> Optional[Scenario]:
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return None

        now = datetime.utcnow()
        scenario.status = "running"
        scenario.updated_at = now
        db.add(scenario)
        db.commit()
        db.refresh(scenario)

        try:
            parameters = scenario.parameters or {}
            model_type = parameters.get("model_type", "arima")
            csv_path = parameters.get("csv_path")
            forecast_steps = int(parameters.get("forecast_steps", 7))
            recommendation_k = int(parameters.get("recommendation_k", 3))
            sku = parameters.get("sku")
            region = parameters.get("region")
            warehouse = parameters.get("warehouse")

            if model_type == "forecast_engine":
                forecast_report = auto_forecast_report(path=csv_path, forecast_steps=forecast_steps)
                forecast_results = {
                    "type": "forecast_engine",
                    "report": forecast_report,
                }
                forecast_series = forecast_report.get("arima", {}).get("forecast", [])
            else:
                if csv_path:
                    series = prepare_series(path=csv_path)
                else:
                    raise ValueError("Scenario parameters must include csv_path for forecast execution")

                if model_type == "arima":
                    model_path = train_and_register(
                        series.tolist(),
                        order=tuple(parameters.get("order", (1, 1, 1))),
                        name="scenario_arima",
                        model_type="arima",
                    )
                    model = load_registered_model(model_path)
                    forecast_values = arima_forecast(model, forecast_steps)
                elif model_type == "xgboost":
                    results = train_xgboost(series.tolist(), n_lags=int(parameters.get("n_lags", 7)))
                    forecast_values = results["future_predictions"]
                elif model_type == "lstm":
                    results = train_lstm(series.tolist(), n_lags=int(parameters.get("n_lags", 7)))
                    forecast_values = results["future_predictions"]
                elif model_type == "prophet":
                    results = train_prophet(series.tolist())
                    if results.get("error"):
                        raise RuntimeError(results["error"])
                    forecast_values = results["future_predictions"]
                else:
                    raise ValueError(f"Unsupported model_type: {model_type}")

                forecast_results = {
                    "type": model_type,
                    "forecast": forecast_values,
                }
                forecast_series = forecast_values

            recommendations = recommend_from_series(
                forecast_series,
                k=recommendation_k,
                sku=sku,
                region=region,
                warehouse=warehouse,
            )

            scenario.status = "completed"
            scenario.last_run_status = "completed"
            scenario.last_run_at = datetime.utcnow()
            scenario.last_run_output = {
                "message": "Scenario executed successfully",
                "parameters": parameters,
                "forecast_results": forecast_results,
                "recommendations": recommendations,
                "completed_at": scenario.last_run_at.isoformat(),
            }
        except Exception as exc:
            scenario.status = "failed"
            scenario.last_run_status = "failed"
            scenario.last_run_at = datetime.utcnow()
            scenario.last_run_output = {
                "message": "Scenario execution failed",
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "parameters": scenario.parameters or {},
                "completed_at": scenario.last_run_at.isoformat(),
            }

        scenario.updated_at = datetime.utcnow()
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario
