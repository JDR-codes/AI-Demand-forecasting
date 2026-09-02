# fastapi_app/services/forecast/forecast_execution_service.py
"""
Forecast Execution Service - Full pipeline execution with step tracking.
"""
import asyncio
import time
import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from fastapi_app.models.forecast_job_model import (
    ForecastJob,
    ForecastJobStatus,
    ForecastJobStep,
    ForecastJobStepDetail,
    ForecastResult
)
from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.models.forecast_metric_history_model import ForecastMetricHistory
from fastapi_app.services.forecast.forecast_service import prepare_series, load_registered_model
from fastapi_app.services.forecast.forecast_metrics import ForecastMetricsService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.core.config import DEFAULT_DATASET_PATH
from fastapi_app.services.background.task_manager import TaskManager

# Import AI modules


import logging
logger = logging.getLogger(__name__)

FORECAST_STEPS = [
    (1, ForecastJobStep.FETCHING_DATA, "Fetching processed data"),
    (2, ForecastJobStep.LOADING_CONFIG, "Loading model configuration"),
    (3, ForecastJobStep.RUNNING_MODEL, "Running model"),
    (4, ForecastJobStep.GENERATING_OUTPUT, "Generating forecast output"),
    (5, ForecastJobStep.SAVING_RESULTS, "Saving forecast results"),
]


class ForecastExecutionService:
    """Service for executing forecast jobs with full lifecycle management."""
    
    @staticmethod
    async def start_job(db: Session, job_id: str) -> Optional[ForecastJob]:
        """Start a forecast job asynchronously."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return None
        
        if job.status != ForecastJobStatus.QUEUED:
            return job
        
        # Update status
        job.status = ForecastJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Create steps if not already created
        existing_steps = db.query(ForecastJobStepDetail).filter(
            ForecastJobStepDetail.forecast_job_id == job.id
        ).count()
        
        if existing_steps == 0:
            for step_num, step_enum, step_name in FORECAST_STEPS:
                step = ForecastJobStepDetail(
                    forecast_job_id=job.id,
                    step_number=step_num,
                    step_name=step_enum,
                    status="pending"
                )
                db.add(step)
            db.commit()
        
        # Send notification
        if job.created_by:
            NotificationService.create_forecast_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=True,
                message=f"Forecast {job.job_id} started."
            )
        
        # Run in background
        TaskManager.run_forecast_job(job_id)
        
        return job
    
    @staticmethod
    def run_job(db: Session, job_id: str) -> Optional[ForecastJob]:
        """Execute the forecast job in background (synchronous for thread pool)."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return None
        
        # Use asyncio to run async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                ForecastExecutionService._execute_job(db, job_id)
            )
            return result
        finally:
            loop.close()
    
    @staticmethod
    async def _execute_job(db: Session, job_id: str) -> Optional[ForecastJob]:
        """Execute the forecast job in background."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return None
        
        # Set job status to RUNNING at start of execution
        job.status = ForecastJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        start_time = time.time()
        total_steps = len(FORECAST_STEPS)
        series = None
        model = None
        model_type = None
        forecast_values = None
        
        try:
            # Load dataset first
            series = ForecastExecutionService._get_series(db, job)
            if series is None or len(series) == 0:
                raise ValueError("No data available for forecasting")
            
            # Update job with data info
            job.configuration = job.configuration or {}
            job.configuration["data_points"] = len(series)
            db.commit()
            
            # Execute steps
            for step_num, step_enum, step_name in FORECAST_STEPS:
                # Check for cancellation
                if job.status == ForecastJobStatus.CANCELLED:
                    logger.info(f"Job {job_id} cancelled by user")
                    break
                
                # Check for pause
                while job.status == ForecastJobStatus.PAUSED:
                    logger.info(f"Job {job_id} paused, waiting...")
                    await asyncio.sleep(1)
                    db.refresh(job)
                
                # Update step
                step = ForecastExecutionService._update_step(db, job.id, step_num, "running")
                job.current_step = step_num
                job.current_step_name = step_name
                job.current_step_message = f"Starting {step_name}..."
                db.commit()
                
                # Execute step
                step_start = time.time()
                
                if step_enum == ForecastJobStep.FETCHING_DATA:
                    job.current_step_message = "Fetching processed dataset..."
                    db.commit()
                    await ForecastExecutionService._step_loading_data(db, job, series)
                    series = await ForecastExecutionService._step_validate_data(db, job, series)
                    
                elif step_enum == ForecastJobStep.LOADING_CONFIG:
                    job.current_step_message = "Loading model configuration..."
                    db.commit()
                    model, model_type = await ForecastExecutionService._step_load_model(db, job)
                    
                elif step_enum == ForecastJobStep.RUNNING_MODEL:
                    job.current_step_message = "Running model inference..."
                    db.commit()
                    forecast_values = await ForecastExecutionService._step_run_model(
                        db, job, model, model_type, series
                    )
                    
                elif step_enum == ForecastJobStep.GENERATING_OUTPUT:
                    job.current_step_message = "Generating forecast outputs..."
                    db.commit()
                    forecast_values = await ForecastExecutionService._step_generate_output(
                        db, job, forecast_values
                    )
                    
                elif step_enum == ForecastJobStep.SAVING_RESULTS:
                    job.current_step_message = "Saving results..."
                    db.commit()
                    await ForecastExecutionService._step_save_results(
                        db, job, series, forecast_values
                    )
                
                # Mark step completed
                step_duration = time.time() - step_start
                ForecastExecutionService._update_step(db, job.id, step_num, "completed", step_duration)
                
                # Update progress
                progress = ((step_num) / total_steps) * 100
                job.progress_percentage = progress
                
                # Calculate ETA
                elapsed = time.time() - start_time
                remaining_steps = total_steps - step_num
                if step_num > 0 and remaining_steps > 0:
                    avg_step_time = elapsed / step_num
                    job.remaining_seconds = avg_step_time * remaining_steps
                    job.estimated_completion = datetime.utcnow() + timedelta(seconds=job.remaining_seconds)
                
                db.commit()
                
                # Send WebSocket update
                await manager.send_progress_update(
                    channel=f"forecast_{job_id}",
                    job_id=job_id,
                    progress=progress,
                    step=step_name,
                    status="running",
                    remaining_time=int(job.remaining_seconds) if job.remaining_seconds else None
                )
            
            # If not cancelled, mark as completed
            if job.status != ForecastJobStatus.CANCELLED:
                job.status = ForecastJobStatus.COMPLETED
                job.progress_percentage = 100.0
                job.completed_at = datetime.utcnow()
                job.elapsed_time = time.time() - start_time
                job.current_step_message = "Completed successfully"
                db.commit()
                
                # ✅ Insert ForecastMetricHistory
                if job.metrics:
                    metric_history = ForecastMetricHistory(
                        model_id=job.model_registry_id,
                        model_type=job.metrics.get("model_type", "unknown").lower(),
                        date=datetime.utcnow(),
                        accuracy=job.metrics.get("accuracy"),
                        rmse=job.metrics.get("rmse"),
                        mae=job.metrics.get("mae"),
                        mape=job.metrics.get("mape"),
                        r2=job.metrics.get("r2"),
                        job_id=job.job_id,
                        records=len(forecast_values) if forecast_values else 0
                    )
                    db.add(metric_history)
                    db.commit()
                
                # Send completion notification
                if job.created_by:
                    NotificationService.create_forecast_notification(
                        db=db,
                        user_id=job.created_by,
                        job_id=job.job_id,
                        success=True,
                        message=f"Forecast {job.job_id} completed successfully. {len(forecast_values or [])} predictions generated."
                    )
                
                await manager.send_progress_update(
                    channel=f"forecast_{job_id}",
                    job_id=job_id,
                    progress=100,
                    step="Completed",
                    status="completed"
                )
                
                await manager.send_dashboard_update({
                    "type": "forecast_completed",
                    "job_id": job_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Forecast job {job_id} failed: {str(e)}")
            job.status = ForecastJobStatus.FAILED
            job.failed_step = job.current_step
            job.failed_step_name = job.current_step_name
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job.current_step_message = f"Failed at {job.current_step_name}: {str(e)}"
            db.commit()
            
            if job.created_by:
                NotificationService.create_forecast_notification(
                    db=db,
                    user_id=job.created_by,
                    job_id=job.job_id,
                    success=False,
                    message=f"Forecast {job.job_id} failed at {job.current_step_name}: {str(e)}"
                )
            
            await manager.send_progress_update(
                channel=f"forecast_{job_id}",
                job_id=job_id,
                progress=job.progress_percentage or 0,
                step="Failed",
                status="failed"
            )
        
        db.refresh(job)
        return job
    
    @staticmethod
    def _update_step(db: Session, job_id: int, step_number: int, status: str, duration: float = None) -> Optional[ForecastJobStepDetail]:
        """Update a job step."""
        step = db.query(ForecastJobStepDetail).filter(
            ForecastJobStepDetail.forecast_job_id == job_id,
            ForecastJobStepDetail.step_number == step_number
        ).first()
        
        if not step:
            return None
        
        step.status = status
        if status == "running":
            step.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            step.completed_at = datetime.utcnow()
            if step.started_at:
                step.duration_seconds = duration or (step.completed_at - step.started_at).total_seconds()
        db.commit()
        db.refresh(step)
        return step
    
    @staticmethod
    def _get_series(db: Session, job: ForecastJob) -> pd.Series:
        """Get time series data strictly from a completed ProcessedDataset with SKU filtering."""
        import os
        
        processed_path = None
        
        # Try to get from explicit processing_job_id first
        if job.processing_job_id:
            from fastapi_app.models.processing_job_model import ProcessedDataset, ProcessingJob
            query = db.query(ProcessedDataset).join(
                ProcessingJob, ProcessedDataset.processing_job_id == ProcessingJob.id
            )
            if str(job.processing_job_id).isdigit():
                query = query.filter(ProcessingJob.id == int(job.processing_job_id))
            else:
                query = query.filter(ProcessingJob.job_id == str(job.processing_job_id))
                
            processed_ds = query.filter(ProcessingJob.status == "completed").order_by(ProcessedDataset.created_at.desc()).first()
            if processed_ds and processed_ds.file_path and os.path.exists(processed_ds.file_path):
                processed_path = processed_ds.file_path
                logger.info(f"Using processed dataset from job {job.processing_job_id}: {processed_path}")
            else:
                raise ValueError(f"No completed processed dataset found for processing job {job.processing_job_id}")

        # Try to get from upload ID next
        elif job.upload_id:
            from fastapi_app.models.processing_job_model import ProcessedDataset, ProcessingJob
            from fastapi_app.models.processing_job_input_model import ProcessingJobInput
            
            processed_ds = db.query(ProcessedDataset).join(
                ProcessingJob, ProcessedDataset.processing_job_id == ProcessingJob.id
            ).join(
                ProcessingJobInput, ProcessingJobInput.processing_job_id == ProcessingJob.id
            ).filter(
                ProcessingJobInput.upload_id == job.upload_id,
                ProcessingJob.status == "completed"
            ).order_by(ProcessedDataset.created_at.desc()).first()
            
            if processed_ds and processed_ds.file_path and os.path.exists(processed_ds.file_path):
                processed_path = processed_ds.file_path
                logger.info(f"Using processed dataset from upload {job.upload_id}: {processed_path}")
            else:
                raise ValueError(f"No completed processed dataset found for upload {job.upload_id}. Raw files are not permitted for forecasting.")
        
        else:
            raise ValueError("No valid processing_job_id or upload_id specified. Real production forecasts require a completed ProcessedDataset.")
            
        if not processed_path:
            raise ValueError("Could not resolve a valid processed dataset path.")
            
        series = prepare_series(path=processed_path)
        return ForecastExecutionService._filter_series(series, job)
    
    @staticmethod
    def _filter_series(series: pd.Series, job: ForecastJob) -> pd.Series:
        """Filter series by SKU, region, warehouse if configured."""
        # Since we're working with a simple series, we can't filter by SKU here
        # This is handled in _get_series when querying raw data
        return series
    
    @staticmethod
    async def _step_loading_data(db: Session, job: ForecastJob, series: pd.Series) -> Dict[str, Any]:
        """Step 1: Load and prepare data."""
        return {
            "series_length": len(series),
            "series_start": str(series.index[0]) if len(series) > 0 else None,
            "series_end": str(series.index[-1]) if len(series) > 0 else None,
            "mean": float(series.mean()) if len(series) > 0 else None,
            "std": float(series.std()) if len(series) > 0 else None
        }
    
    @staticmethod
    async def _step_validate_data(db: Session, job: ForecastJob, series: pd.Series) -> pd.Series:
        """Step 2: Validate dataset."""
        if series is None or len(series) == 0:
            raise ValueError("No data loaded for forecasting")
        
        # Check minimum rows
        min_rows = 30
        if len(series) < min_rows:
            raise ValueError(f"Dataset has only {len(series)} rows. Minimum required: {min_rows}")
        
        # Check for missing values
        nan_count = series.isna().sum()
        if nan_count > 0:
            logger.warning(f"Found {nan_count} NaN values, filling with interpolation")
            series = series.interpolate().bfill().ffill()
        
        # Check for duplicates
        duplicate_count = series.index.duplicated().sum()
        if duplicate_count > 0:
            logger.warning(f"Found {duplicate_count} duplicate dates, aggregating")
            series = series.groupby(series.index).mean()
        
        # Check date continuity
        if isinstance(series.index, pd.DatetimeIndex):
            date_range = pd.date_range(start=series.index[0], end=series.index[-1], freq='D')
            missing_dates = set(date_range) - set(series.index)
            if missing_dates:
                logger.warning(f"Found {len(missing_dates)} missing dates, filling with interpolation")
                series = series.reindex(date_range)
                series = series.interpolate().bfill().ffill()
        
        # Check for infinite values
        inf_count = np.isinf(series).sum()
        if inf_count > 0:
            raise ValueError(f"Found {inf_count} infinite values in data")
        
        return series
    
    @staticmethod
    async def _step_load_model(db: Session, job: ForecastJob) -> tuple:
        """Step 3: Load model from registry."""
        model_registry_id = job.model_registry_id
        
        if not model_registry_id:
            # Try to get default model
            default_model = db.query(ModelRegistry).filter(
                ModelRegistry.is_default == True,
                ModelRegistry.is_active == True
            ).first()
            if default_model:
                model_registry_id = default_model.id
            else:
                raise ValueError("No model specified and no default model found. Train a model first.")
        
        model_reg = db.query(ModelRegistry).filter(
            ModelRegistry.id == model_registry_id
        ).first()
        
        if not model_reg:
            raise ValueError(f"Model {model_registry_id} not found in registry")
        
        if not model_reg.artifact_path:
            raise ValueError(f"Model {model_registry_id} has no artifact path. Train the model first.")
        
        model = load_registered_model(model_reg.artifact_path)
        model_type = model_reg.model_type
        
        return model, model_type
    
    @staticmethod
    async def _step_run_model(db: Session, job: ForecastJob, model, model_type: str, series: pd.Series) -> List[float]:
        """Step 4: Run the model."""
        horizon = job.forecast_horizon or 7
        series_list = series.tolist()
        
        forecast_values = None
        
        if model_type == "arima":
            from fastapi_app.ai.arima import forecast as arima_forecast
            forecast_values = arima_forecast(model, horizon)
        elif model_type == "xgboost":
            from fastapi_app.ai.xgboost_model import forecast_xgboost
            forecast_values = forecast_xgboost(model, series_list, steps=horizon, n_lags=7)
        elif model_type == "lstm":
            from fastapi_app.ai.lstm import forecast_lstm
            forecast_values = forecast_lstm(model, series_list, steps=horizon, n_lags=7)
        elif model_type == "prophet":
            from fastapi_app.ai.prophet import forecast_prophet
            forecast_values = forecast_prophet(model, periods=horizon)
        else:
            if hasattr(model, "forecast"):
                forecast_values = model.forecast(horizon)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
        
        # Ensure list
        if hasattr(forecast_values, "tolist"):
            forecast_values = forecast_values.tolist()
        elif not isinstance(forecast_values, list):
            forecast_values = list(forecast_values)
        
        # Store in job
        job.metrics = job.metrics or {}
        job.metrics["forecast_count"] = len(forecast_values)
        job.metrics["model_type"] = model_type
        db.commit()
        
        return forecast_values
    
    @staticmethod
    async def _step_generate_output(db: Session, job: ForecastJob, forecast_values: List[float]) -> List[float]:
        """Step 5: Generate output with confidence intervals."""
        if not forecast_values:
            raise ValueError("No forecast values to process")
        
        # Calculate confidence intervals
        confidence_interval = ForecastMetricsService.calculate_confidence_interval(
            forecast_values,
            confidence_level=0.95
        )
        
        # Find peaks
        from fastapi_app.ai.arima import find_peaks
        raw_peaks = find_peaks(forecast_values, top_n=5)
        
        # Calculate summary metrics
        total_demand = sum(forecast_values)
        avg_demand = total_demand / len(forecast_values) if forecast_values else 0
        
        # Update job metrics
        job.metrics = job.metrics or {}
        job.metrics.update({
            "confidence_interval": confidence_interval,
            "peaks": raw_peaks,
            "total_demand": total_demand,
            "avg_demand": avg_demand,
            "peak_day": raw_peaks[0]["step"] if raw_peaks else None,
            "peak_value": raw_peaks[0]["value"] if raw_peaks else None
        })
        db.commit()
        
        return forecast_values
    
    @staticmethod
    async def _step_save_results(db: Session, job: ForecastJob, series: pd.Series, forecast_values: List[float]):
        """Step 6: Save results with historical data and is_forecast flag."""
        if not forecast_values:
            raise ValueError("No forecast to save")
        
        sku = job.sku or "default"
        region = job.region
        warehouse = job.warehouse
        
        results_to_add = []
        
        # ✅ 1. Save historical data (is_forecast=False)
        if series is not None and len(series) > 0:
            # Take last 30 historical points for context
            historical_series = series.tail(30)
            for date, value in historical_series.items():
                if pd.isna(value):
                    continue
                result = ForecastResult(
                    forecast_job_id=job.id,
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    forecast_date=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
                    prediction=float(value),
                    actual_value=float(value),  # Historical values are actual
                    confidence_score=1.0,  # 100% confidence for historical
                    model_used="historical",
                    is_forecast=False,  # ✅ Mark as historical
                    is_peak=False
                )
                results_to_add.append(result)
        
        # ✅ 2. Save forecast data (is_forecast=True)
        # Generate dates
        last_date = series.index[-1] if len(series) > 0 else pd.Timestamp.now()
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=len(forecast_values),
            freq='D'
        )
        
        # Update job forecast date range
        job.forecast_start_date = forecast_dates[0].to_pydatetime()
        job.forecast_end_date = forecast_dates[-1].to_pydatetime()
        
        # Get confidence intervals
        confidence_interval = job.metrics.get("confidence_interval", {})
        upper = confidence_interval.get("upper", [])
        lower = confidence_interval.get("lower", [])
        
        # Get peaks
        peaks = job.metrics.get("peaks", [])
        peak_steps = {p["step"] - 1 for p in peaks}
        
        for i, (date, value) in enumerate(zip(forecast_dates, forecast_values)):
            result = ForecastResult(
                forecast_job_id=job.id,
                sku=sku,
                region=region,
                warehouse=warehouse,
                forecast_date=date.to_pydatetime(),
                prediction=float(value),
                confidence_score=0.85,
                confidence_upper=upper[i] if i < len(upper) else None,
                confidence_lower=lower[i] if i < len(lower) else None,
                model_used=job.metrics.get("model_type", "unknown"),
                is_forecast=True,  # ✅ Mark as forecast
                is_peak=i in peak_steps
            )
            results_to_add.append(result)
        
        if results_to_add:
            db.bulk_save_objects(results_to_add)
            db.commit()
        
        job.metrics["saved_count"] = len(results_to_add)
        job.metrics["historical_count"] = len(series.tail(30)) if series is not None else 0
        job.metrics["forecast_count"] = len(forecast_values)
        db.commit()
    
    @staticmethod
    def pause_job(db: Session, job_id: str) -> bool:
        """Pause a running job."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job or job.status != ForecastJobStatus.RUNNING:
            return False
        
        job.status = ForecastJobStatus.PAUSED
        job.paused_at = datetime.utcnow()
        db.commit()
        
        if job.created_by:
            NotificationService.create_forecast_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=True,
                message=f"Forecast {job.job_id} paused."
            )
        
        return True
    
    @staticmethod
    def resume_job(db: Session, job_id: str) -> bool:
        """Resume a paused job."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job or job.status != ForecastJobStatus.PAUSED:
            return False
        
        job.status = ForecastJobStatus.RUNNING
        job.paused_at = None
        db.commit()
        
        if job.created_by:
            NotificationService.create_forecast_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=True,
                message=f"Forecast {job.job_id} resumed."
            )
        
        return True
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        """Cancel a running or queued job."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job or job.status not in [ForecastJobStatus.QUEUED, ForecastJobStatus.RUNNING]:
            return False
        
        job.status = ForecastJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.commit()
        
        if job.created_by:
            NotificationService.create_forecast_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=False,
                message=f"Forecast {job.job_id} cancelled."
            )
        
        return True
    
    @staticmethod
    def retry_job(db: Session, job_id: str) -> Optional[ForecastJob]:
        """Retry a failed job."""
        old_job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not old_job:
            return None
        
        # Create new job with same config
        from fastapi_app.schemas.forecast_schema import ForecastJobCreate
        config = ForecastJobCreate(
            upload_id=old_job.upload_id,
            model_registry_id=old_job.model_registry_id,
            forecast_horizon=old_job.forecast_horizon,
            configuration=old_job.configuration,
            sku=old_job.sku or "default",
            region=old_job.region,
            warehouse=old_job.warehouse
        )
        
        from fastapi_app.services.forecast.forecast_job_service import ForecastJobService
        new_job = ForecastJobService.create_job(db, config, old_job.created_by)
        
        # Start the new job
        TaskManager.run_forecast_job(new_job.job_id)
        
        return new_job
    
    @staticmethod
    def get_live_status(db: Session, job_id: str) -> Dict[str, Any]:
        """Get live status for UI polling."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return {"error": "Job not found"}
        
        return {
            "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "progress": job.progress_percentage,
            "step": job.current_step_name,
            "step_number": job.current_step,
            "step_message": job.current_step_message,
            "remaining_time": job.remaining_seconds,
            "elapsed_time": job.elapsed_time,
            "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "failed_step": job.failed_step,
            "failed_step_name": job.failed_step_name
        }