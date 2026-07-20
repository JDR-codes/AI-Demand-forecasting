#fastapi_app/services/forecast/forecast_runner.py

"""
Forecast Runner - Loads models and generates forecasts.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
import logging

from fastapi_app.models.forecast_job_model import (
    ForecastJob,
    ForecastJobStatus,
    ForecastJobStep,
    ForecastResult
)
from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.services.forecast.forecast_service import (
    prepare_series,
    load_registered_model,
)
from fastapi_app.services.forecast.forecast_metrics import ForecastMetricsService
from fastapi_app.core.config import DEFAULT_DATASET_PATH

# Import forecast functions directly from AI modules
from fastapi_app.ai.arima import forecast as arima_forecast, find_peaks
from fastapi_app.ai.xgboost_model import forecast_xgboost
from fastapi_app.ai.lstm import forecast_lstm
from fastapi_app.ai.prophet import forecast_prophet

# ✅ Import notification service
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.models.notification_model import NotificationType, NotificationPriority

logger = logging.getLogger(__name__)


class ForecastRunner:
    """Executes forecast jobs - loads model, generates forecast, saves results."""
    
    def __init__(self, db: Session, job: ForecastJob):
        self.db = db
        self.job = job
        self.series = None
        self.model = None
        self.model_type = None
        self.forecast = None
        self.metrics = {}
        self._commit_count = 0
        
    def run(self) -> Dict[str, Any]:
        """Run the complete forecast pipeline."""
        steps = [
            (1, "Load Model", self._step_load_model),
            (2, "Load Dataset", self._step_load_dataset),
            (3, "Validate Data", self._step_validate_data),
            (4, "Generate Forecast", self._step_generate_forecast),
            (5, "Post Processing", self._step_post_processing),
            (6, "Save Results", self._step_save_results)
        ]
        
        total_steps = len(steps)
        
        try:
            for step_number, step_name, step_func in steps:
                if self.job.status == ForecastJobStatus.CANCELLED:
                    break
                
                self._update_step(step_number, step_name, "running")
                progress = ((step_number - 1) / total_steps) * 100
                self._update_progress(progress)
                
                try:
                    result = step_func()
                    self._update_step(step_number, step_name, "completed")
                    self.metrics.update(result)
                except Exception as e:
                    logger.error(f"Step {step_name} failed: {str(e)}")
                    self._update_step(step_number, step_name, "failed", error=str(e))
                    raise
            
            self._update_progress(100.0)
            
            # ✅ Mark job as completed
            self.job.status = ForecastJobStatus.COMPLETED
            self.job.completed_at = datetime.utcnow()
            self.job.elapsed_time = (self.job.completed_at - self.job.started_at).total_seconds() if self.job.started_at else 0
            self.db.commit()
            
            # ✅ Create notification for successful completion
            if self.job.created_by:
                NotificationService.create_forecast_notification(
                    db=self.db,
                    user_id=self.job.created_by,
                    job_id=self.job.job_id,
                    success=True,
                    message=f"Forecast {self.job.job_id} completed successfully. {len(self.forecast)} predictions generated."
                )
            
            return {
                "forecast": self.forecast,
                "metrics": self.metrics
            }
            
        except Exception as e:
            # ✅ Mark job as failed
            self.job.status = ForecastJobStatus.FAILED
            self.job.error_message = str(e)
            self.job.completed_at = datetime.utcnow()
            self.db.commit()
            
            # ✅ Create notification for failure
            if self.job.created_by:
                NotificationService.create_forecast_notification(
                    db=self.db,
                    user_id=self.job.created_by,
                    job_id=self.job.job_id,
                    success=False,
                    message=f"Forecast {self.job.job_id} failed: {str(e)}"
                )
            
            raise
    
    def _step_load_model(self) -> Dict[str, Any]:
        """Step 1: Load model from registry."""
        model_registry_id = self.job.model_registry_id
        
        if not model_registry_id:
            raise ValueError("No model registry ID provided. Train a model first.")
        
        model_reg = self.db.query(ModelRegistry).filter(
            ModelRegistry.id == model_registry_id
        ).first()
        
        if not model_reg:
            raise ValueError(f"Model {model_registry_id} not found in registry")
        
        if not model_reg.artifact_path:
            raise ValueError(f"Model {model_registry_id} has no artifact path")
        
        self.model = load_registered_model(model_reg.artifact_path)
        self.model_type = model_reg.model_type
        self.metrics["model_type"] = self.model_type
        self.metrics["model_loaded"] = True
        self.metrics["model_version"] = model_reg.version
        
        return {"model_source": "registry", "model_type": self.model_type}
    
    def _step_load_dataset(self) -> Dict[str, Any]:
        """Step 2: Load dataset."""
        self.series = self._get_series()
        
        return {
            "series_length": len(self.series),
            "series_start": str(self.series.index[0]) if len(self.series) > 0 else None,
            "series_end": str(self.series.index[-1]) if len(self.series) > 0 else None
        }
    
    def _step_validate_data(self) -> Dict[str, Any]:
        """Step 3: Validate data."""
        if self.series is None or len(self.series) == 0:
            raise ValueError("No data loaded for forecasting")
        
        nan_count = self.series.isna().sum()
        if nan_count > 0:
            logger.warning(f"Found {nan_count} NaN values, filling with interpolation")
            self.series = self.series.interpolate().bfill().ffill()
        
        inf_count = np.isinf(self.series).sum()
        if inf_count > 0:
            raise ValueError(f"Found {inf_count} infinite values in data")
        
        return {"validated": True, "length": len(self.series), "nan_filled": nan_count}
    
    def _step_generate_forecast(self) -> Dict[str, Any]:
        """Step 4: Generate forecast using the appropriate model."""
        horizon = self.job.forecast_horizon or 7
        
        if not self.model:
            raise ValueError("No model loaded")
        
        series_list = self.series.tolist()
        
        if self.model_type == "arima":
            self.forecast = arima_forecast(self.model, horizon)
            
        elif self.model_type == "xgboost":
            self.forecast = forecast_xgboost(
                self.model,
                series_list,
                steps=horizon,
                n_lags=7
            )
            
        elif self.model_type == "lstm":
            self.forecast = forecast_lstm(
                self.model,
                series_list,
                steps=horizon,
                n_lags=7
            )
            
        elif self.model_type == "prophet":
            self.forecast = forecast_prophet(self.model, periods=horizon)
            
        else:
            if hasattr(self.model, "forecast"):
                self.forecast = self.model.forecast(horizon)
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
        
        if hasattr(self.forecast, "tolist"):
            self.forecast = self.forecast.tolist()
        elif not isinstance(self.forecast, list):
            self.forecast = list(self.forecast)
        
        self.metrics["forecast_length"] = len(self.forecast)
        
        return {
            "forecast": self.forecast,
            "horizon": horizon,
            "forecast_length": len(self.forecast)
        }
    
    def _step_post_processing(self) -> Dict[str, Any]:
        """Step 5: Post-processing."""
        if not self.forecast:
            raise ValueError("No forecast to process")
        
        confidence_interval = ForecastMetricsService.calculate_confidence_interval(
            self.forecast,
            confidence_level=0.95
        )
        self.metrics["confidence_interval"] = confidence_interval
        self.metrics["confidence_score"] = 0.85
        
        raw_peaks = find_peaks(self.forecast, top_n=5)
        self.metrics["peaks"] = raw_peaks
        
        return {"peaks": raw_peaks, "confidence_interval": confidence_interval}
    
    def _step_save_results(self) -> Dict[str, Any]:
        """Step 6: Save results with bulk insert."""
        if not self.forecast:
            raise ValueError("No forecast to save")
        
        last_date = self.series.index[-1] if len(self.series) > 0 else pd.Timestamp.now()
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=len(self.forecast),
            freq='D'
        )
        
        confidence_interval = self.metrics.get("confidence_interval", {})
        upper = confidence_interval.get("upper", [])
        lower = confidence_interval.get("lower", [])
        
        raw_peaks = self.metrics.get("peaks", [])
        peak_steps = {p["step"] - 1 for p in raw_peaks}
        
        results_to_add = []
        sku = self.job.configuration.get("sku", "default")
        region = self.job.configuration.get("region")
        warehouse = self.job.configuration.get("warehouse")
        
        for i, (date, value) in enumerate(zip(forecast_dates, self.forecast)):
            result = ForecastResult(
                forecast_job_id=self.job.id,
                sku=sku,
                region=region,
                warehouse=warehouse,
                forecast_date=date.to_pydatetime(),
                prediction=float(value),
                confidence_score=self.metrics.get("confidence_score", 0.85),
                confidence_upper=upper[i] if i < len(upper) else None,
                confidence_lower=lower[i] if i < len(lower) else None,
                model_used=self.model_type,
                is_peak=i in peak_steps
            )
            results_to_add.append(result)
        
        if results_to_add:
            self.db.bulk_save_objects(results_to_add)
            self.db.commit()
        
        return {"saved_count": len(results_to_add)}
    
    def _get_series(self) -> pd.Series:
        """Get the series from upload or default dataset."""
        if self.series is not None:
            return self.series
        
        upload_id = self.job.upload_id
        if upload_id:
            from fastapi_app.models.upload_model import Upload
            upload = self.db.query(Upload).filter(Upload.id == upload_id).first()
            if upload and upload.file_path:
                try:
                    return prepare_series(path=upload.file_path)
                except Exception as e:
                    logger.warning(f"Could not load series from upload: {str(e)}")
        
        return prepare_series(path=DEFAULT_DATASET_PATH)
    
    def _update_progress(self, progress: float):
        """Update job progress."""
        self.job.progress_percentage = progress
        self._commit_count += 1
        if self._commit_count % 3 == 0 or progress >= 100:
            self.db.commit()
            self._commit_count = 0
    
    def _update_step(self, step_number: int, step_name: str, status: str, error: str = None):
        """Update a job step."""
        step = self.db.query(ForecastJobStep).filter(
            ForecastJobStep.forecast_job_id == self.job.id,
            ForecastJobStep.step_number == step_number
        ).first()
        
        if step:
            step.status = status
            if status == "running":
                step.started_at = datetime.utcnow()
            elif status in ["completed", "failed"]:
                step.completed_at = datetime.utcnow()
                if step.started_at:
                    step.duration_seconds = (step.completed_at - step.started_at).total_seconds()
            if error:
                step.message = error
            
            self.db.commit()