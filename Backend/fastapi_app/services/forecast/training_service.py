# fastapi_app/services/forecast/training_service.py
"""
Training Service - Creates training jobs and delegates model registry operations.
"""
import uuid
import time
import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from fastapi_app.models.training_job_model import TrainingJob, TrainingStatus, TrainingJobStepDetail, TrainingStep, TrainingHistory
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.forecast_metric_history_model import ForecastMetricHistory
from fastapi_app.schemas.forecast_schema import TrainingJobCreate
from fastapi_app.services.forecast.model_registry_service import ModelRegistryService
from fastapi_app.services.forecast.forecast_service import (
    prepare_series,
    train_xgboost,
    train_lstm,
    train_prophet,
    train_transformer,
    train_random_forest,
    train_sarima,
    train_and_register,
)
from fastapi_app.core.config import DEFAULT_DATASET_PATH, MODELS_DIR
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.models.notification_model import NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

# Training steps
TRAINING_STEPS = [
    (1, TrainingStep.PROCESSING_DATA, "Processing Data"),
    (2, TrainingStep.VALIDATION, "Validating Data"),
    (3, TrainingStep.TRAINING, "Training Model"),
    (4, TrainingStep.EVALUATION, "Evaluating Model"),
    (5, TrainingStep.SAVING_MODEL, "Saving Model"),
]


class TrainingService:
    """Service for managing training jobs."""
    
    @staticmethod
    def create_job(
        db: Session,
        config: TrainingJobCreate,
        created_by: int = None
    ) -> TrainingJob:
        """Create a new training job."""
        configuration = config.configuration or {}
        configuration.update({
            "batch_size": config.batch_size or 16,
            "learning_rate": config.learning_rate or 0.001,
            "epochs": config.epochs or 20,
            "created_by": created_by
        })
        
        clean_model_type = config.model_type.lower().replace("-", "_")
        
        job = TrainingJob(
            job_id=str(uuid.uuid4()),
            model_type=clean_model_type,
            model_registry_id=config.model_registry_id,
            upload_id=config.upload_id,
            processing_job_id=config.processing_job_id,
            csv_path=None,
            configuration=configuration,
            total_epochs=config.epochs or 20,
            status=TrainingStatus.QUEUED,
            progress_percentage=0.0
        )
        
        db.add(job)
        db.flush()
        
        # Create training steps
        for step_num, step_enum, step_name in TRAINING_STEPS:
            step = TrainingJobStepDetail(
                training_job_id=job.job_id,
                step_number=step_num,
                step_name=step_enum,
                status="pending"
            )
            db.add(step)
        
        db.commit()
        db.refresh(job)
        return job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[TrainingJob]:
        """Get a training job by ID."""
        return db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
    
    @staticmethod
    def get_jobs(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TrainingJob]:
        """Get training jobs with optional filtering."""
        query = db.query(TrainingJob)
        if status:
            query = query.filter(TrainingJob.status == status)
        return query.order_by(desc(TrainingJob.created_at)).offset(offset).limit(limit).all()
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        """Cancel a training job."""
        job = TrainingService.get_job(db, job_id)
        if not job:
            return False
        
        if job.status in [TrainingStatus.QUEUED, TrainingStatus.RUNNING]:
            job.status = TrainingStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def _update_step(db: Session, job_id: str, step_number: int, status: str, duration: float = None, message: str = None):
        """Update a training step."""
        step = db.query(TrainingJobStepDetail).filter(
            TrainingJobStepDetail.training_job_id == job_id,
            TrainingJobStepDetail.step_number == step_number
        ).first()
        
        if not step:
            return
        
        step.status = status
        if status == "running":
            step.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            step.completed_at = datetime.utcnow()
            if step.started_at:
                step.duration_seconds = duration or (step.completed_at - step.started_at).total_seconds()
        if message:
            step.message = message
        db.commit()
    
    @staticmethod
    def _get_version_from_history(db: Session, model_registry_id: str) -> str:
        """Generate next version number."""
        history = db.query(TrainingHistory).filter(
            TrainingHistory.model_registry_id == model_registry_id
        ).order_by(TrainingHistory.trained_at.desc()).first()
        
        if not history:
            return "1.0.0"
        
        parts = history.version.split('.')
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            patch += 1
            if patch >= 10:
                patch = 0
                minor += 1
                if minor >= 10:
                    minor = 0
                    major += 1
            return f"{major}.{minor}.{patch}"
        except:
            return "1.0.0"
    
    @staticmethod
    def run_job(db: Session, job_id: str) -> Optional[TrainingJob]:
        """Execute a training job with step tracking."""
        job = TrainingService.get_job(db, job_id)
        if not job:
            return None
        
        if job.status != TrainingStatus.QUEUED:
            return job
        
        job.status = TrainingStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        start_time = time.time()
        total_steps = len(TRAINING_STEPS)
        model = None
        model_type = job.model_type.lower().replace("-", "_")
        
        try:
            # Step 1: Processing Data
            TrainingService._update_step(db, job.job_id, 1, "running", message="Loading and preparing data...")
            job.current_step = 1
            job.current_step_name = "Processing Data"
            job.current_step_message = "Loading dataset..."
            job.progress_percentage = 5.0
            db.commit()
            
            # Load series safely
            series = None
            dataset_source = None
            import os
            
            if job.processing_job_id:
                dataset_source = f"processing job {job.processing_job_id}"
                from fastapi_app.models.processing_job_model import ProcessedDataset, ProcessingJob
                
                query = db.query(ProcessedDataset).join(
                    ProcessingJob, ProcessedDataset.processing_job_id == ProcessingJob.id
                )
                if str(job.processing_job_id).isdigit():
                    query = query.filter(ProcessingJob.id == int(job.processing_job_id))
                else:
                    query = query.filter(ProcessingJob.job_id == str(job.processing_job_id))
                    
                processed_ds = query.filter(ProcessingJob.status == "completed").order_by(ProcessedDataset.created_at.desc()).first()
                if not processed_ds or not processed_ds.file_path or not os.path.exists(processed_ds.file_path):
                    raise ValueError(f"Processed dataset file for processing job {job.processing_job_id} not found on disk")
                
                logger.info(f"Using processed dataset: {processed_ds.file_path}")
                series = prepare_series(path=processed_ds.file_path)
                
            elif job.upload_id:
                dataset_source = f"upload {job.upload_id}"
                upload = db.query(Upload).filter(Upload.id == job.upload_id).first()
                if not upload:
                    raise ValueError(f"Upload record for upload ID {job.upload_id} not found")
                
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
                
                if not processed_ds or not processed_ds.file_path or not os.path.exists(processed_ds.file_path):
                    raise ValueError(f"No completed processed dataset found for upload {job.upload_id}. Raw files cannot be used directly for training.")
                
                logger.info(f"Using processed dataset from upload: {processed_ds.file_path}")
                series = prepare_series(path=processed_ds.file_path)
                
            else:
                raise ValueError("No valid processing_job_id or upload_id specified. Real production forecasts require a completed ProcessedDataset.")
            
            if series is None or len(series) == 0:
                raise ValueError("No data available for training")
            
            training_values = series.tolist()
            dataset_size = len(training_values)
            
            job.current_step_message = f"Loaded {dataset_size} records"
            job.progress_percentage = 10.0
            db.commit()
            
            TrainingService._update_step(db, job.job_id, 1, "completed", message=f"Loaded {dataset_size} records")
            
            # Step 1: Check cancellation at end of step 1
            db.refresh(job)
            if job.status == TrainingStatus.CANCELLED:
                logger.info(f"Training job {job_id} cancelled after Step 1")
                return job
                
            # Step 2: Validation
            TrainingService._update_step(db, job.job_id, 2, "running", message="Validating data quality...")
            job.current_step = 2
            job.current_step_name = "Validating Data"
            job.current_step_message = "Checking data quality..."
            job.progress_percentage = 15.0
            db.commit()
            
            # Validate data
            if len(training_values) < 30:
                raise ValueError(f"Dataset has only {len(training_values)} rows. Minimum required: 30")
            
            # Check for NaN/Inf
            import numpy as np
            nan_count = sum(1 for v in training_values if np.isnan(v))
            inf_count = sum(1 for v in training_values if np.isinf(v))
            if nan_count > 0 or inf_count > 0:
                raise ValueError(f"Data contains {nan_count} NaN and {inf_count} Inf values")
            
            job.current_step_message = f"Data validated: {len(training_values)} valid records"
            job.progress_percentage = 20.0
            db.commit()
            
            TrainingService._update_step(db, job.job_id, 2, "completed", message="Data validation passed")
            
            # Step 2: Check cancellation at end of step 2
            db.refresh(job)
            if job.status == TrainingStatus.CANCELLED:
                logger.info(f"Training job {job_id} cancelled after Step 2")
                return job

            # Step 3: Training
            TrainingService._update_step(db, job.job_id, 3, "running", message=f"Training {model_type.upper()} model...")
            job.current_step = 3
            job.current_step_name = "Training Model"
            job.current_step_message = f"Training {model_type.upper()} model..."
            job.progress_percentage = 25.0
            db.commit()
            
            # Resolve Model Registry Configuration
            resolved_config = {
                "epochs": 20,
                "batch_size": 16,
                "learning_rate": 0.001,
                "validation_split": 0.2,
                "seasonality": True,
                "n_lags": 7,
                "order": (1, 1, 1),
                "seasonal_order": (1, 1, 1, 12) if model_type == "sarima" else (0, 0, 0, 0)
            }
            
            # Load config from database config if parent model registry is specified
            if job.model_registry_id:
                from fastapi_app.models.training_configuration_model import TrainingConfiguration
                db_config = db.query(TrainingConfiguration).filter(
                    TrainingConfiguration.model_registry_id == job.model_registry_id
                ).first()
                if db_config:
                    resolved_config["epochs"] = db_config.epochs or 20
                    resolved_config["batch_size"] = db_config.batch_size or 16
                    resolved_config["learning_rate"] = db_config.learning_rate or 0.001
                    resolved_config["validation_split"] = db_config.validation_split or 0.2
                    resolved_config["seasonality"] = db_config.seasonality if db_config.seasonality is not None else True
                    
            # Overwrite with job-specific overrides if provided
            if job.configuration:
                for k, v in job.configuration.items():
                    if v is not None:
                        resolved_config[k] = v

            epoch_start = 25
            total_epochs = resolved_config["epochs"]
            
            # Train based on model type
            result = None
            if model_type == "arima":
                job.current_step_message = "Training ARIMA model..."
                db.commit()
                
                result = train_sarima(
                    training_values, 
                    order=resolved_config["order"], 
                    seasonal_order=(0, 0, 0, 0)
                )
                if "error" in result:
                    raise ValueError(result["error"])
                
                # Progress for ARIMA (fast)
                job.progress_percentage = 60.0
                job.current_epoch = 1
                job.current_step_message = "ARIMA training completed"
                db.commit()
                
            elif model_type == "xgboost":
                # Simulated epoch progress callbacks
                for epoch in range(1, min(total_epochs, 10) + 1):
                    # Check cancellation inside simulation loop
                    db.refresh(job)
                    if job.status == TrainingStatus.CANCELLED:
                        logger.info(f"Training job {job_id} cancelled during training loop")
                        return job
                    job.current_epoch = epoch
                    job.progress_percentage = epoch_start + (epoch / min(total_epochs, 10)) * 35
                    job.current_step_message = f"Training XGBoost epoch {epoch}/{min(total_epochs, 10)}"
                    db.commit()
                    time.sleep(0.3)
                
                result = train_xgboost(
                    training_values, 
                    n_lags=resolved_config["n_lags"],
                    test_frac=resolved_config["validation_split"]
                )
                if "error" in result:
                    raise ValueError(result["error"])
                    
                job.progress_percentage = 60.0
                db.commit()
                
            elif model_type == "lstm":
                for epoch in range(1, min(total_epochs, 20) + 1):
                    db.refresh(job)
                    if job.status == TrainingStatus.CANCELLED:
                        logger.info(f"Training job {job_id} cancelled during training loop")
                        return job
                    job.current_epoch = epoch
                    job.progress_percentage = epoch_start + (epoch / min(total_epochs, 20)) * 35
                    job.current_step_message = f"Training LSTM epoch {epoch}/{min(total_epochs, 20)}"
                    db.commit()
                    time.sleep(0.4)
                
                result = train_lstm(
                    training_values, 
                    n_lags=resolved_config["n_lags"], 
                    test_frac=resolved_config["validation_split"],
                    epochs=resolved_config["epochs"], 
                    batch_size=resolved_config["batch_size"]
                )
                if "error" in result:
                    raise ValueError(result["error"])
                    
                job.progress_percentage = 60.0
                db.commit()
                
            elif model_type == "prophet":
                result = train_prophet(
                    training_values, 
                    test_frac=resolved_config["validation_split"]
                )
                if result.get("error"):
                    raise ValueError(result["error"])
                
                job.progress_percentage = 60.0
                db.commit()
                
            elif model_type == "transformer":
                # Simulate epochs progress
                for epoch in range(1, min(total_epochs, 10) + 1):
                    db.refresh(job)
                    if job.status == TrainingStatus.CANCELLED:
                        logger.info(f"Training job {job_id} cancelled during training loop")
                        return job
                    job.current_epoch = epoch
                    job.progress_percentage = epoch_start + (epoch / min(total_epochs, 10)) * 35
                    job.current_step_message = f"Training Transformer epoch {epoch}/{min(total_epochs, 10)}"
                    db.commit()
                    time.sleep(0.3)
                    
                result = train_transformer(
                    training_values, 
                    n_lags=resolved_config["n_lags"], 
                    test_frac=resolved_config["validation_split"],
                    epochs=resolved_config["epochs"], 
                    batch_size=resolved_config["batch_size"]
                )
                if result.get("error"):
                    raise ValueError(result["error"])
                
                job.progress_percentage = 60.0
                db.commit()
                
            elif model_type == "random_forest":
                result = train_random_forest(
                    training_values, 
                    n_lags=resolved_config["n_lags"], 
                    test_frac=resolved_config["validation_split"]
                )
                if result.get("error"):
                    raise ValueError(result["error"])
                
                job.progress_percentage = 60.0
                db.commit()
                
            elif model_type == "sarima":
                result = train_sarima(
                    training_values, 
                    order=resolved_config["order"], 
                    seasonal_order=resolved_config["seasonal_order"]
                )
                if result.get("error"):
                    raise ValueError(result["error"])
                
                job.progress_percentage = 60.0
                db.commit()
                
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            # Map metrics to job record
            metrics = result.get("metrics", {})
            mape = metrics.get("mape", 0)
            accuracy = metrics.get("accuracy", float(max(0.0, 1.0 - (mape / 100.0))))
            
            job.metrics = {
                "accuracy": accuracy,
                "rmse": metrics.get("rmse", 0),
                "mae": metrics.get("mae", 0),
                "mape": mape,
                "r2": metrics.get("r2", 0),
                "training_loss": metrics.get("training_loss"),
                "validation_loss": metrics.get("validation_loss")
            }
            db.commit()
            
            TrainingService._update_step(db, job.job_id, 3, "completed", message="Model training completed")
            
            # Step 3: Check cancellation at end of step 3
            db.refresh(job)
            if job.status == TrainingStatus.CANCELLED:
                logger.info(f"Training job {job_id} cancelled after Step 3")
                return job
                
            # Step 4: Evaluation
            TrainingService._update_step(db, job.job_id, 4, "running", message="Evaluating model performance...")
            job.current_step = 4
            job.current_step_name = "Evaluating Model"
            job.current_step_message = "Calculating metrics..."
            job.progress_percentage = 70.0
            db.commit()
            
            # Calculate improvement compared to base model
            previous_best = None
            accuracy_before = None
            if job.model_registry_id:
                previous_best = db.query(TrainingHistory).filter(
                    TrainingHistory.model_registry_id == job.model_registry_id
                ).order_by(TrainingHistory.trained_at.desc()).first()
                if previous_best:
                    accuracy_before = previous_best.accuracy_after
                    
            accuracy_after = accuracy
            
            improvement = None
            if accuracy_before is not None and accuracy_after is not None:
                improvement = ((accuracy_after - accuracy_before) / accuracy_before * 100) if accuracy_before > 0 else None
            
            job.current_step_message = f"Accuracy: {accuracy_after:.1%}" if accuracy_after else "Metrics calculated"
            job.progress_percentage = 80.0
            db.commit()
            
            TrainingService._update_step(db, job.job_id, 4, "completed", message=f"Accuracy: {accuracy_after:.1%}" if accuracy_after else "Evaluation complete")
            
            # Step 4: Check cancellation at end of step 4
            db.refresh(job)
            if job.status == TrainingStatus.CANCELLED:
                logger.info(f"Training job {job_id} cancelled after Step 4")
                return job

            # Step 5: Saving Model
            TrainingService._update_step(db, job.job_id, 5, "running", message="Saving model to registry...")
            job.current_step = 5
            job.current_step_name = "Saving Model"
            job.current_step_message = "Registering model..."
            job.progress_percentage = 90.0
            db.commit()
            
            # Resolve or Create Model Registry Row
            from fastapi_app.models.model_registry_model import ModelRegistry
            model = None
            if job.model_registry_id:
                model = db.query(ModelRegistry).filter(ModelRegistry.id == job.model_registry_id).first()
                
            if not model:
                # Generate new Model Registry Row
                model_name = f"{model_type.upper()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                model = ModelRegistry(
                    id=str(uuid.uuid4()),
                    name=model_name,
                    model_type=model_type,
                    status="active",
                    is_active=True,
                    is_default=False,
                    deployment_status="development"
                )
                db.add(model)
                db.flush()
                job.model_registry_id = model.id
                db.commit()
                
            # Auto-generate next version string from history
            version = TrainingService._get_version_from_history(db, model.id)
            
            # Save artifact file to disk (Durable flow for all models)
            model_dir = os.path.join(MODELS_DIR, model_type, model.id, version)
            os.makedirs(model_dir, exist_ok=True)
            model_path = os.path.join(model_dir, "model.pkl")
            
            import joblib
            try:
                joblib.dump(result.get("model"), model_path)
            except Exception as dump_err:
                logger.error(f"Failed to dump model using joblib: {dump_err}, falling back to pickle")
                import pickle
                with open(model_path, "wb") as f:
                    pickle.dump(result.get("model"), f)
                    
            artifact_size = os.path.getsize(model_path) if os.path.exists(model_path) else 0
            
            # Calculate dataset hash
            import hashlib
            data_str = str(training_values).encode('utf-8')
            dataset_hash = hashlib.sha256(data_str).hexdigest()
            
            # Build lineage metadata
            meta_info = {
                "processing_job_id": job.processing_job_id,
                "upload_id": job.upload_id,
                "dataset_source": dataset_source,
                "dataset_row_count": dataset_size,
                "trained_at": datetime.utcnow().isoformat(),
                "configuration_used": resolved_config
            }
            
            # Update Model Registry properties
            model.last_trained = datetime.utcnow()
            model.best_accuracy = accuracy
            model.best_rmse = metrics.get("rmse")
            model.best_mae = metrics.get("mae")
            model.best_mape = mape
            model.best_r2 = metrics.get("r2")
            model.best_loss = metrics.get("training_loss")
            model.training_duration = (datetime.utcnow() - job.started_at).total_seconds() if job.started_at else 0
            model.version = version
            model.training_size = dataset_size
            model.artifact_path = model_path
            model.artifact_size = artifact_size
            model.dataset_hash = dataset_hash
            model.meta_info = meta_info
            model.hyperparameters = resolved_config
            
            db.commit()
            
            # Record training history
            history = ModelRegistryService.record_training_history(
                db=db,
                model_registry_id=model.id,
                training_job_id=job.job_id,
                version=version,
                accuracy_before=accuracy_before,
                accuracy_after=accuracy_after,
                improvement_percentage=improvement,
                rmse_before=previous_best.rmse_after if previous_best else None,
                rmse_after=metrics.get("rmse"),
                mae_before=previous_best.mae_after if previous_best else None,
                mae_after=metrics.get("mae"),
                mape_before=previous_best.mape_after if previous_best else None,
                mape_after=mape,
                duration_seconds=model.training_duration,
                epochs=total_epochs,
                dataset_size=dataset_size,
                metrics=job.metrics,
                trained_by=None,
                started_at=job.started_at,
                finished_at=datetime.utcnow()
            )
            
            job.current_step_message = "Model registered successfully"
            job.progress_percentage = 95.0
            db.commit()
            
            # Insert ForecastMetricHistory (Use lowercase model_type)
            metric_history = ForecastMetricHistory(
                model_id=model.id,
                model_type=model_type.lower(),
                date=datetime.utcnow(),
                accuracy=accuracy,
                rmse=metrics.get("rmse"),
                mae=metrics.get("mae"),
                mape=mape,
                r2=metrics.get("r2"),
                job_id=job.job_id,
                records=dataset_size
            )
            db.add(metric_history)
            db.commit()
            
            TrainingService._update_step(db, job.job_id, 5, "completed", message="Model saved to registry")
            
            # Mark job as completed
            job.status = TrainingStatus.COMPLETED
            job.progress_percentage = 100.0
            job.completed_at = datetime.utcnow()
            job.elapsed_time = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
            job.current_step_message = "Training completed successfully"
            db.commit()
            
            # Send Notification
            if job.created_by:
                NotificationService.create_training_notification(
                    db=db,
                    user_id=job.created_by,
                    model_type=model_type.upper(),
                    success=True,
                    accuracy=accuracy,
                    message=f"{model_type.upper()} training completed successfully. Accuracy: {accuracy:.1%}"
                )
            
            return job
            
        except Exception as e:
            logger.error(f"Training job {job_id} failed: {str(e)}")
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            job.failed_step = job.current_step
            job.failed_step_name = job.current_step_name
            job.completed_at = datetime.utcnow()
            job.current_step_message = f"Failed at {job.current_step_name}: {str(e)}"
            db.commit()
            
            # Update currently failing step in table
            TrainingService._update_step(
                db, 
                job.job_id, 
                job.current_step or 1, 
                "failed", 
                message=str(e)
            )
            
            if job.created_by:
                NotificationService.create_training_notification(
                    db=db,
                    user_id=job.created_by,
                    model_type=model_type.upper(),
                    success=False,
                    message=f"{model_type.upper()} training failed: {str(e)}"
                )
            
            return job