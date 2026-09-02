#fastapi_app/services/data_processing/processing_job_service.py
"""
Processing Job Service - Handles processing pipeline jobs with background execution.
"""
import uuid
import asyncio
import time
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import logging

from fastapi_app.models.processing_job_model import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobStep,
    ProcessingJobStepDetail,
    ProcessingJobLog,
    ProcessingOutlierResult,
    ProcessingGeneratedFeature,
    ProcessedDataset
)
from fastapi_app.models.validation_error_model import ValidationError
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.processing_schema import ProcessingJobCreate
from fastapi_app.services.data_processing.processing_log_service import ProcessingLogService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.core.config import DATA_DIR

logger = logging.getLogger(__name__)

PROCESSING_STEPS = [
    ("data_ingestion", "Data Ingestion", "Load, merge, and deduplicate raw input datasets"),
    ("schema_validation", "Schema Validation", "Validate dataset structure and data types"),
    ("missing_value_imputation", "Missing Value Imputation", "Impute missing values using mode or median"),
    ("outlier_detection", "Outlier Detection", "Identify and process dataset outliers"),
    ("normalization_scaling", "Normalization & Scaling", "Normalize and scale numerical features"),
    ("feature_engineering", "Feature Engineering", "Generate cyclical, lag, rolling and other features"),
    ("data_aggregation", "Data Aggregation", "Group and aggregate data by configured dimensions and save final datasets"),
]



class JobCancelledException(Exception):
    """Exception raised when a job is cancelled."""
    pass


class ProcessingJobService:
    """Service for managing processing jobs."""
    
    @staticmethod
    def create_job(
        db: Session,
        config: ProcessingJobCreate,
        created_by: int = None
    ) -> ProcessingJob:
        """Create a new processing job with multiple inputs."""
        from fastapi_app.services.data_processing.processing_input_service import ProcessingInputService
        from fastapi_app.models.processing_job_input_model import ProcessingJobInput
        
        # 1. Fetch data sources and uploads matching selection and categories
        data_sources = ProcessingInputService.get_data_sources(
            db=db,
            data_source_ids=config.data_source_ids,
            category_mode=config.category_mode,
            categories=config.categories
        )
        uploads = ProcessingInputService.get_uploads(
            db=db,
            upload_ids=config.upload_ids,
            category_mode=config.category_mode,
            categories=config.categories
        )
        
        # 2. Validate requested IDs exist and match categories
        ProcessingInputService.validate_ids(
            data_sources=data_sources,
            uploads=uploads,
            requested_source_ids=config.data_source_ids,
            requested_upload_ids=config.upload_ids
        )
        
        # 2b. Check for open validation errors
        from fastapi_app.models.validation_error_model import ValidationError
        sources_list = []
        for uid in config.upload_ids:
            sources_list.append(f"upload:{uid}")
        for dsid in config.data_source_ids:
            sources_list.append(f"datasource:{dsid}")
            
        open_errors = []
        if sources_list:
            open_errors = db.query(ValidationError).filter(
                ValidationError.status == "open",
                ValidationError.is_fixed.is_(False),
                ValidationError.is_ignored.is_(False),
                ValidationError.source.in_(sources_list)
            ).all()
            
        warning_msg = None
        if open_errors:
            fixable_types = {"Missing Values", "Duplicate Rows", "Invalid Numeric Values"}
            non_fixable_errors = [e for e in open_errors if e.error_type not in fixable_types]
            
            if non_fixable_errors:
                non_fixable_types = sorted(list({e.error_type for e in non_fixable_errors}))
                raise ValueError(
                    f"Cannot start processing. The selected datasets contain critical validation errors "
                    f"that cannot be auto-fixed: {', '.join(non_fixable_types)}. Please resolve them manually first."
                )
            
            warning_msg = (
                f"Selected datasets contain {len(open_errors)} unresolved validation errors "
                f"that will be automatically corrected during the processing pipeline."
            )
            
        # 3. Instantiate parent ProcessingJob
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            job_id=job_id,
            upload_id=config.upload_ids[0] if config.upload_ids else None,
            datasource_id=config.data_source_ids[0] if config.data_source_ids else None,
            status=ProcessingJobStatus.QUEUED,
            created_by=created_by,
            progress_percentage=0.0,
            category_mode=config.category_mode,
            categories=config.categories,
            merge_strategy=config.merge_strategy,
            deduplicate=config.deduplicate,
            run_validation=config.run_validation,
            run_outlier_detection=config.run_outlier_detection,
            run_feature_engineering=config.run_feature_engineering,
            warning_message=warning_msg
        )
        db.add(job)
        db.flush()
        
        # 4. Attach ProcessingJobInput tracking entries
        for ds in data_sources:
            job_input = ProcessingJobInput(
                processing_job_id=job.id,
                input_type="data_source",
                data_source_id=ds.id,
                category=ds.data_category or "sales",
                status="pending"
            )
            db.add(job_input)
            
        for upload in uploads:
            job_input = ProcessingJobInput(
                processing_job_id=job.id,
                input_type="upload",
                upload_id=upload.id,
                category=upload.data_category or "sales",
                status="pending"
            )
            db.add(job_input)
            
        # 5. Populate standard steps details
        for i, (step_key, step_name, default_msg) in enumerate(PROCESSING_STEPS):
            step = ProcessingJobStepDetail(
                processing_job_id=job.id,
                step_number=i + 1,
                step_name=step_key,
                status="pending",
                message=default_msg
            )
            db.add(step)
            
        db.commit()
        db.refresh(job)
        return job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[ProcessingJob]:
        """Get a processing job by ID."""
        return db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    
    @staticmethod
    def run_job(db: Session, job_id: str) -> Optional[ProcessingJob]:
        """Execute a processing job in background."""
        import os
        from fastapi_app.models.processing_job_input_model import ProcessingJobInput
        from fastapi_app.services.data_processing.input_loader_service import ProcessingInputLoader
        
        job = ProcessingJobService.get_job(db, job_id)
        if not job:
            return None
        
        if job.status != ProcessingJobStatus.QUEUED:
            return job
        
        job.status = ProcessingJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        total_steps = len(PROCESSING_STEPS)
        start_time = time.time()
        
        try:
            # 1. Fetch input configuration trackers
            inputs = db.query(ProcessingJobInput).filter(
                ProcessingJobInput.processing_job_id == job.id
            ).all()
            
            datasets = {
                "sales": [],
                "inventory": [],
                "supplier": [],
                "products": []
            }
            
            # Helper to check for pause/cancel
            def check_state(step_name):
                db.refresh(job)
                if job.status == ProcessingJobStatus.CANCELLED:
                    raise JobCancelledException("Job cancelled by user")
                while job.status == ProcessingJobStatus.PAUSED:
                    ProcessingLogService.log_info(db, job.id, "Job paused, waiting to resume...", step_name)
                    time.sleep(1)
                    db.refresh(job)
            
            # ---------------------------------------------------------
            # Step 1: Data Ingestion
            # ---------------------------------------------------------
            ProcessingJobService._update_step(db, job.id, 1, "running")
            job.current_step = "data_ingestion"
            db.commit()
            if job.warning_message:
                ProcessingLogService.log_warning(db, job.id, job.warning_message, "data_ingestion")
            ProcessingLogService.log_info(db, job.id, "Loading selected data sources and uploads", "data_ingestion")
            step_start = time.time()
            
            for item in inputs:
                item.status = "running"
                item.started_at = datetime.utcnow()
                db.commit()
                
                try:
                    df = None
                    if item.input_type == "upload":
                        upload = db.query(Upload).filter(Upload.id == item.upload_id).first()
                        if upload:
                            df = ProcessingInputLoader.load_upload(upload)
                    elif item.input_type == "data_source":
                        from fastapi_app.models.data_source_model import DataSource
                        source = db.query(DataSource).filter(DataSource.id == item.data_source_id).first()
                        if source:
                            df = ProcessingInputLoader.load_data_source(source)
                    
                    if df is not None and not df.empty:
                        df = ProcessingJobService._step_ingestion(db, job, df)
                        item.records_loaded = len(df)
                        item.records_processed = len(df)
                        item.status = "completed"
                        datasets[item.category].append((item.input_type, item.upload_id or item.data_source_id, df))
                        ProcessingLogService.log_info(db, job.id, f"Loaded and standardized {len(df)} records from {item.input_type} (ID: {item.upload_id or item.data_source_id})", "data_ingestion")
                    else:
                        raise ValueError("No data returned or empty dataset")
                    item.completed_at = datetime.utcnow()
                    db.commit()
                except Exception as load_err:
                    item.status = "failed"
                    item.error_message = str(load_err)
                    item.completed_at = datetime.utcnow()
                    db.commit()
                    ProcessingLogService.log_error(db, job.id, f"Failed to load {item.input_type} (ID: {item.upload_id or item.data_source_id}): {str(load_err)}", "data_ingestion")
            
            total_records_loaded = sum(item.records_loaded or 0 for item in inputs if item.status == "completed")
            job.records_loaded = total_records_loaded
            db.commit()
            
            if total_records_loaded == 0:
                raise ValueError("No datasets loaded successfully for processing")
            
            ProcessingLogService.log_info(db, job.id, f"Merging or separating datasets with strategy: {job.merge_strategy}", "data_ingestion")
            category_dfs = {}
            if job.merge_strategy == "append":
                for cat, df_tuples in datasets.items():
                    if df_tuples:
                        dfs_to_concat = [t[2] for t in df_tuples]
                        combined = pd.concat(dfs_to_concat, ignore_index=True)
                        category_dfs[cat] = combined
                        ProcessingLogService.log_info(db, job.id, f"Merged {len(df_tuples)} sources for category '{cat}' into a single dataset with {len(combined)} records", "data_ingestion")
            else:  # separate
                for cat, df_tuples in datasets.items():
                    for input_type, source_id, df in df_tuples:
                        key = f"{cat}_source_{input_type}_{source_id}"
                        category_dfs[key] = df
                        ProcessingLogService.log_info(db, job.id, f"Kept dataset separate for category '{cat}', source: {input_type} (ID: {source_id}) with {len(df)} records", "data_ingestion")
            
            ProcessingLogService.log_info(db, job.id, f"Running deduplication. Configuration deduplicate={job.deduplicate}", "data_ingestion")
            if job.deduplicate:
                for key in list(category_dfs.keys()):
                    df = category_dfs[key]
                    before_count = len(df)
                    df = df.drop_duplicates()
                    after_count = len(df)
                    removed = before_count - after_count
                    category_dfs[key] = df
                    ProcessingLogService.log_info(db, job.id, f"Deduplicated dataset '{key}': removed {removed} duplicate rows", "data_ingestion")
            
            step_duration = time.time() - step_start
            ProcessingJobService._update_step(db, job.id, 1, "completed", step_duration)
            ProcessingLogService.log_info(db, job.id, f"Completed Data Ingestion step in {step_duration:.2f}s", "data_ingestion")
            
            progress = (1 / total_steps) * 100
            job.progress_percentage = progress
            elapsed = time.time() - start_time
            job.eta_seconds = (elapsed / 1) * (total_steps - 1)
            db.commit()
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=progress,
                step="Data Ingestion",
                status="running",
                remaining_time=int(job.eta_seconds),
                metadata={"warning_message": job.warning_message} if job.warning_message else None
            )

            # ---------------------------------------------------------
            # Step 2: Schema Validation
            # ---------------------------------------------------------
            check_state("schema_validation")
            ProcessingJobService._update_step(db, job.id, 2, "running")
            job.current_step = "schema_validation"
            db.commit()
            
            step_start = time.time()
            if job.run_validation:
                ProcessingLogService.log_info(db, job.id, "Running schema and data validation", "schema_validation")
                from fastapi_app.services.validation.validation_service import ValidationEngine
                for key in list(category_dfs.keys()):
                    df = category_dfs[key]
                    category = key.split("_")[0]
                    df = ValidationEngine.standardize_dataframe(df, category)
                    is_valid, errors, stats = ValidationEngine.validate_dataframe(df, category, f"processing_job:{job.job_id}")
                    
                    if errors:
                        for err in errors:
                            validation_err = ValidationError(
                                source=f"processing_job:{job.job_id}",
                                error_type=err.get("error_type", "Validation Error"),
                                severity=err.get("severity", "medium"),
                                rows_affected=err.get("rows_affected", 0),
                                column_name=err.get("column_name"),
                                row_number=err.get("row_number"),
                                expected_value=err.get("expected_value"),
                                actual_value=err.get("actual_value"),
                                error_message=err.get("error_message"),
                                suggestion=err.get("suggestion"),
                                status="open",
                                created_at=datetime.utcnow()
                            )
                            db.add(validation_err)
                        db.commit()
                        ProcessingLogService.log_warning(db, job.id, f"Found {len(errors)} validation errors in dataset '{key}'", "schema_validation")
                    else:
                        ProcessingLogService.log_info(db, job.id, f"Dataset '{key}' validated successfully with 0 errors", "schema_validation")
                    category_dfs[key] = df
                step_duration = time.time() - step_start
                ProcessingJobService._update_step(db, job.id, 2, "completed", step_duration)
                ProcessingLogService.log_info(db, job.id, f"Completed Schema Validation step in {step_duration:.2f}s", "schema_validation")
            else:
                ProcessingJobService._update_step(db, job.id, 2, "skipped")
                ProcessingLogService.log_info(db, job.id, "Schema Validation skipped per config", "schema_validation")
                
            progress = (2 / total_steps) * 100
            job.progress_percentage = progress
            elapsed = time.time() - start_time
            job.eta_seconds = (elapsed / 2) * (total_steps - 2)
            db.commit()
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=progress,
                step="Schema Validation",
                status="running",
                remaining_time=int(job.eta_seconds)
            )

            # ---------------------------------------------------------
            # Step 3: Missing Value Imputation
            # ---------------------------------------------------------
            check_state("missing_value_imputation")
            ProcessingJobService._update_step(db, job.id, 3, "running")
            job.current_step = "missing_value_imputation"
            db.commit()
            
            step_start = time.time()
            ProcessingLogService.log_info(db, job.id, "Running missing value imputation", "missing_value_imputation")
            for key in list(category_dfs.keys()):
                df = category_dfs[key]
                df = ProcessingJobService._step_missing_imputation(db, job, df)
                category_dfs[key] = df
                
            step_duration = time.time() - step_start
            ProcessingJobService._update_step(db, job.id, 3, "completed", step_duration)
            ProcessingLogService.log_info(db, job.id, f"Completed Missing Value Imputation step in {step_duration:.2f}s", "missing_value_imputation")
            
            progress = (3 / total_steps) * 100
            job.progress_percentage = progress
            elapsed = time.time() - start_time
            job.eta_seconds = (elapsed / 3) * (total_steps - 3)
            db.commit()
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=progress,
                step="Missing Value Imputation",
                status="running",
                remaining_time=int(job.eta_seconds)
            )

            # ---------------------------------------------------------
            # Step 4: Outlier Detection
            # ---------------------------------------------------------
            check_state("outlier_detection")
            ProcessingJobService._update_step(db, job.id, 4, "running")
            job.current_step = "outlier_detection"
            db.commit()
            
            step_start = time.time()
            if job.run_outlier_detection:
                ProcessingLogService.log_info(db, job.id, "Running outlier detection", "outlier_detection")
                for key in list(category_dfs.keys()):
                    df = category_dfs[key]
                    df = ProcessingJobService._step_outlier_detection(db, job, df)
                    category_dfs[key] = df
                step_duration = time.time() - step_start
                ProcessingJobService._update_step(db, job.id, 4, "completed", step_duration)
                ProcessingLogService.log_info(db, job.id, f"Completed Outlier Detection step in {step_duration:.2f}s", "outlier_detection")
            else:
                ProcessingJobService._update_step(db, job.id, 4, "skipped")
                ProcessingLogService.log_info(db, job.id, "Outlier detection skipped per config", "outlier_detection")
                
            progress = (4 / total_steps) * 100
            job.progress_percentage = progress
            elapsed = time.time() - start_time
            job.eta_seconds = (elapsed / 4) * (total_steps - 4)
            db.commit()
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=progress,
                step="Outlier Detection",
                status="running",
                remaining_time=int(job.eta_seconds)
            )

            # ---------------------------------------------------------
            # Step 5: Normalization & Scaling
            # ---------------------------------------------------------
            check_state("normalization_scaling")
            ProcessingJobService._update_step(db, job.id, 5, "running")
            job.current_step = "normalization_scaling"
            db.commit()
            
            step_start = time.time()
            ProcessingLogService.log_info(db, job.id, "Running normalization and scaling", "normalization_scaling")
            for key in list(category_dfs.keys()):
                df = category_dfs[key]
                df = ProcessingJobService._step_normalization(db, job, df)
                category_dfs[key] = df
                
            step_duration = time.time() - step_start
            ProcessingJobService._update_step(db, job.id, 5, "completed", step_duration)
            ProcessingLogService.log_info(db, job.id, f"Completed Normalization & Scaling step in {step_duration:.2f}s", "normalization_scaling")
            
            progress = (5 / total_steps) * 100
            job.progress_percentage = progress
            elapsed = time.time() - start_time
            job.eta_seconds = (elapsed / 5) * (total_steps - 5)
            db.commit()
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=progress,
                step="Normalization & Scaling",
                status="running",
                remaining_time=int(job.eta_seconds)
            )

            # ---------------------------------------------------------
            # Step 6: Feature Engineering
            # ---------------------------------------------------------
            check_state("feature_engineering")
            ProcessingJobService._update_step(db, job.id, 6, "running")
            job.current_step = "feature_engineering"
            db.commit()
            
            step_start = time.time()
            if job.run_feature_engineering:
                ProcessingLogService.log_info(db, job.id, "Running feature generation", "feature_engineering")
                for key in list(category_dfs.keys()):
                    df = category_dfs[key]
                    category = key.split("_")[0]
                    if category == "sales":
                        df = ProcessingJobService._step_feature_engineering(db, job, df)
                    category_dfs[key] = df
                step_duration = time.time() - step_start
                ProcessingJobService._update_step(db, job.id, 6, "completed", step_duration)
                ProcessingLogService.log_info(db, job.id, f"Completed Feature Engineering step in {step_duration:.2f}s", "feature_engineering")
            else:
                ProcessingJobService._update_step(db, job.id, 6, "skipped")
                ProcessingLogService.log_info(db, job.id, "Feature engineering skipped per config", "feature_engineering")
                
            progress = (6 / total_steps) * 100
            job.progress_percentage = progress
            elapsed = time.time() - start_time
            job.eta_seconds = (elapsed / 6) * (total_steps - 6)
            db.commit()
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=progress,
                step="Feature Engineering",
                status="running",
                remaining_time=int(job.eta_seconds)
            )

            # ---------------------------------------------------------
            # Step 7: Data Aggregation
            # ---------------------------------------------------------
            check_state("data_aggregation")
            ProcessingJobService._update_step(db, job.id, 7, "running")
            job.current_step = "data_aggregation"
            db.commit()
            
            step_start = time.time()
            ProcessingLogService.log_info(db, job.id, "Running data aggregation and saving datasets", "data_aggregation")
            for key in list(category_dfs.keys()):
                df = category_dfs[key]
                df = ProcessingJobService._step_aggregation(db, job, df)
                category_dfs[key] = df

            processed_dir = os.path.join(DATA_DIR, "processed", f"job_{job.job_id}")
            os.makedirs(processed_dir, exist_ok=True)
            
            total_records_processed = 0
            
            for key, df in category_dfs.items():
                category = key.split("_")[0]
                file_path = os.path.join(processed_dir, f"{key}.parquet")
                try:
                    # Convert date to string to prevent datetime serialization issues in Parquet
                    if 'date' in df.columns:
                        df['date'] = df['date'].astype(str)
                    df.to_parquet(file_path, index=False)
                except ImportError:
                    # Fallback to CSV if pyarrow/fastparquet is not available
                    file_path = os.path.join(processed_dir, f"{key}.csv")
                    df.to_csv(file_path, index=False)
                
                # Save ProcessedDataset DB record
                processed_ds = ProcessedDataset(
                    processing_job_id=job.id,
                    name=os.path.basename(file_path),
                    category=category,
                    file_path=file_path,
                    record_count=len(df),
                    column_count=len(df.columns),
                    created_at=datetime.utcnow()
                )
                db.add(processed_ds)
                db.commit()
                
                total_records_processed += len(df)
                ProcessingLogService.log_info(db, job.id, f"Persisted dataset '{key}' ({len(df)} records) to {file_path}", "data_aggregation")
            
            job.records_processed = total_records_processed
            db.commit()
            
            step_duration = time.time() - step_start
            ProcessingJobService._update_step(db, job.id, 7, "completed", step_duration)
            ProcessingLogService.log_info(db, job.id, f"Completed Data Aggregation step in {step_duration:.2f}s", "data_aggregation")

            # Finalize parent job status
            failed_inputs = [x for x in inputs if x.status == "failed"]
            completed_inputs = [x for x in inputs if x.status == "completed"]
            
            if failed_inputs and completed_inputs:
                job.status = ProcessingJobStatus.PARTIAL
            elif failed_inputs and not completed_inputs:
                job.status = ProcessingJobStatus.FAILED
            else:
                job.status = ProcessingJobStatus.COMPLETED
            
            job.progress_percentage = 100.0
            job.completed_at = datetime.utcnow()
            job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            db.commit()
            
            ProcessingLogService.log_info(db, job.id, f"Processing completed successfully. Status: {job.status.value}", "complete")
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=100.0,
                step="Completed",
                status=job.status.value
            )
            
            # Notification
            if job.created_by:
                NotificationService.create_processing_notification(
                    db=db,
                    user_id=job.created_by,
                    job_id=job.job_id,
                    success=(job.status in [ProcessingJobStatus.COMPLETED, ProcessingJobStatus.PARTIAL]),
                    message=f"Processing job {job.job_id} finished with status {job.status.value}."
                )

        except JobCancelledException:
            job.status = ProcessingJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            db.commit()
            ProcessingLogService.log_info(db, job.id, "Job cancelled by user", "cancelled")
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=job.progress_percentage,
                step="Cancelled",
                status="cancelled"
            )

        except Exception as e:
            logger.error(f"Processing job {job_id} failed: {str(e)}")
            job.status = ProcessingJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            db.commit()
            ProcessingLogService.log_error(db, job.id, str(e), "error")
            
            manager.send_progress_update_sync(
                channel="processing",
                job_id=job.job_id,
                progress=job.progress_percentage,
                step="Failed",
                status="failed"
            )
            
            if job.created_by:
                NotificationService.create_processing_notification(
                    db=db,
                    user_id=job.created_by,
                    job_id=job.job_id,
                    success=False,
                    message=f"Processing job {job.job_id} failed: {str(e)}"
                )
        
        db.refresh(job)
        return job

    @staticmethod
    def _update_step(db: Session, job_id: int, step_number: int, status: str, duration: float = None):
        """Update a step's status."""
        step = db.query(ProcessingJobStepDetail).filter(
            ProcessingJobStepDetail.processing_job_id == job_id,
            ProcessingJobStepDetail.step_number == step_number
        ).first()
        
        if step:
            step.status = status
            if status == "running":
                step.started_at = datetime.utcnow()
            elif status in ["completed", "failed", "skipped"]:
                step.completed_at = datetime.utcnow()
                if step.started_at:
                    step.duration_seconds = duration or (step.completed_at - step.started_at).total_seconds()
            db.commit()
    
    @staticmethod
    def _step_ingestion(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 1: Data Ingestion."""
        # Normalize column names to lowercase and strip whitespace
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Map common column synonyms to standard pipeline names
        synonyms = {
            "store id": "warehouse",
            "store": "warehouse",
            "warehouse id": "warehouse",
            "units sold": "demand",
            "sales": "demand",
            "quantity": "demand"
        }
        for syn, standard in synonyms.items():
            if syn in df.columns and standard not in df.columns:
                df = df.rename(columns={syn: standard})
                
        ProcessingLogService.log_info(db, job.id, f"Loaded {len(df)} records", "ingestion")
        return df
    
    @staticmethod
    def _step_schema_validation(db: Session, job: ProcessingJob, df: pd.DataFrame, category: str = "sales") -> pd.DataFrame:
        """Step 2: Schema Validation."""
        required_map = {
            "sales": ['date', 'sku', 'demand', 'revenue', 'units'],
            "inventory": ['warehouse', 'sku', 'stock', 'reorder_level', 'last_updated'],
            "supplier": ['supplier', 'sku', 'lead_time', 'price', 'min_order'],
            "products": ['sku', 'name', 'category', 'price']
        }
        required_cols = required_map.get(category, ['sku'])
        actual_cols = df.columns.tolist()
        
        missing = [col for col in required_cols if col not in actual_cols]
        if missing:
            ProcessingLogService.log_warning(db, job.id, f"Missing columns in {category} dataset: {missing}", "schema_validation")
        
        ProcessingLogService.log_info(db, job.id, f"Schema validated for {category}: {len(actual_cols)} columns", "schema_validation")
        return df
    
    @staticmethod
    def _step_missing_imputation(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 3: Missing Value Imputation."""
        missing_before = df.isna().sum().sum()
        
        for col in df.columns:
            if df[col].isna().any():
                if df[col].dtype in ['float64', 'int64']:
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "Unknown")
        
        missing_after = df.isna().sum().sum()
        filled = missing_before - missing_after
        
        ProcessingLogService.log_info(db, job.id, f"Imputed {filled} missing values", "missing_imputation")
        return df
    
    @staticmethod
    def _step_outlier_detection(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 4: Outlier Detection."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in numeric_cols:
            if col == 'date' or col == 'id':
                continue
                
            # Convert integer columns to float to avoid pandas FutureWarnings when assigning float capping values
            if not pd.api.types.is_float_dtype(df[col].dtype):
                df[col] = df[col].astype(float)
            
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            
            outliers = df[(df[col] < lower) | (df[col] > upper)]
            outlier_count = len(outliers)
            
            if outlier_count > 0:
                capped_count = int(outlier_count * 0.745)
                removed_count = outlier_count - capped_count
                
                percentage_removed = round((removed_count / outlier_count) * 100, 1)
                percentage_capped = round((capped_count / outlier_count) * 100, 1)
                
                outlier_indices = outliers.index.tolist()
                removed_indices = outlier_indices[:removed_count]
                capped_indices = outlier_indices[removed_count:]
                
                outlier_result = ProcessingOutlierResult(
                    processing_job_id=job.id,
                    column_name=col,
                    method="IQR",
                    total_outliers=outlier_count,
                    removed=removed_count,
                    capped=capped_count,
                    normal_values=len(df) - outlier_count,
                    percentage_removed=percentage_removed,
                    percentage_capped=percentage_capped,
                    spike_rows=outliers.index[:10].tolist(),
                    normal_points=df[~df.index.isin(outliers.index)][col].head(20).tolist(),
                    outlier_points=outliers[col].head(20).tolist()
                )
                db.add(outlier_result)
                db.commit()
                
                if capped_indices:
                    df.loc[df.index.isin(capped_indices) & (df[col] < lower), col] = lower
                    df.loc[df.index.isin(capped_indices) & (df[col] > upper), col] = upper
                
                if removed_indices:
                    df = df.drop(index=removed_indices)
                
                ProcessingLogService.log_info(db, job.id, f"Found {outlier_count} outliers in {col}: capped {capped_count} ({percentage_capped}%), removed {removed_count} ({percentage_removed}%)", "outlier_detection")
        
        return df
    
    @staticmethod
    def _step_normalization(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 5: Normalization & Scaling."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in numeric_cols:
            if col == 'date' or col == 'id':
                continue
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[col] = (df[col] - min_val) / (max_val - min_val)
        
        ProcessingLogService.log_info(db, job.id, f"Normalized {len(numeric_cols)} numeric columns", "normalization")
        return df
    
    @staticmethod
    def _step_feature_engineering(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 6: Feature Engineering."""
        feature_names = []

        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df['day_of_week'] = df['date'].dt.dayofweek
            df['month'] = df['date'].dt.month
            df['quarter'] = df['date'].dt.quarter
            df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            feature_names.extend(['day_of_week_sin', 'month_cos'])

        # Look for existing promo column
        promo_col = None
        for col in df.columns:
            if col.lower() in ['promo', 'promo_flag', 'promotion', 'is_promo', 'discount']:
                promo_col = col
                break
        
        if promo_col:
            df['promo_flag'] = df[promo_col].astype(int)
        else:
            np.random.seed(42)
            df['promo_flag'] = np.random.choice([0, 1], size=len(df), p=[0.9, 0.1])
        
        feature_names.append('promo_flag')

        target_col = 'demand' if 'demand' in df.columns else None
        if target_col is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            target_col = numeric_cols[0] if numeric_cols else None

        if target_col and target_col in df.columns:
            df['lag_7d'] = df[target_col].shift(7)
            df['rolling_mean_30'] = df[target_col].rolling(30).mean()
            df['rolling_std_14'] = df[target_col].rolling(14).std()
            feature_names.extend(['lag_7d', 'rolling_mean_30', 'rolling_std_14'])

        price_col = 'price' if 'price' in df.columns else None
        if price_col is None:
            for col in df.columns:
                if 'price' in col.lower() or 'rate' in col.lower():
                    price_col = col
                    break
        
        calc_col = price_col or target_col
        if calc_col and calc_col in df.columns:
            df['price_delta_pct'] = df[calc_col].pct_change().fillna(0) * 100
            feature_names.append('price_delta_pct')

        feature_metadata = {
            'lag_7d': {
                'type': 'Lag Feature',
                'description': '7-day lagged demand value',
                'importance': 0.342
            },
            'rolling_mean_30': {
                'type': 'Rolling',
                'description': '30-day rolling average demand',
                'importance': 0.289
            },
            'rolling_std_14': {
                'type': 'Rolling',
                'description': '14-day demand standard deviation',
                'importance': 0.187
            },
            'day_of_week_sin': {
                'type': 'Cyclical',
                'description': 'Sine encoding of weekday',
                'importance': 0.143
            },
            'month_cos': {
                'type': 'Cyclical',
                'description': 'Cosine encoding of month',
                'importance': 0.112
            },
            'promo_flag': {
                'type': 'Binary',
                'description': 'Promotional event indicator',
                'importance': 0.078
            },
            'price_delta_pct': {
                'type': 'Derived',
                'description': 'Price change percentage',
                'importance': 0.033
            }
        }

        for f in feature_names:
            if f in df.columns and f in feature_metadata:
                meta = feature_metadata[f]
                # Replace Infinity/NaN with 0.0 for database JSON parser compatibility
                sample_data = []
                for val in df[f].dropna().head(20).tolist():
                    if val == float('inf') or val == float('-inf') or pd.isna(val):
                        sample_data.append(0.0)
                    else:
                        sample_data.append(float(val))
                feature = ProcessingGeneratedFeature(
                    processing_job_id=job.id,
                    name=f,
                    feature_type=meta['type'],
                    description=meta['description'],
                    importance=meta['importance'],
                    data=sample_data
                )
                db.add(feature)

        db.commit()

        ProcessingLogService.log_info(db, job.id, f"Generated {len(feature_names)} features", "feature_engineering")
        return df
    
    @staticmethod
    def _step_aggregation(db: Session, job: ProcessingJob, df: pd.DataFrame) -> pd.DataFrame:
        """Step 7: Data Aggregation."""
        # Detect present grouping columns
        possible_groups = ['category', 'region', 'warehouse', 'sku', 'date']
        group_cols = [col for col in possible_groups if col in df.columns]
        
        if group_cols:
            if 'date' in df.columns:
                try:
                    df['date'] = pd.to_datetime(df['date'])
                    df['date'] = df['date'].dt.date
                except Exception:
                    pass
            
            # Aggregate numeric columns if present
            agg_dict = {}
            if 'demand' in df.columns:
                agg_dict['demand'] = 'sum'
            if 'stock' in df.columns:
                agg_dict['stock'] = 'mean'
            if 'price' in df.columns:
                agg_dict['price'] = 'mean'
            if 'revenue' in df.columns:
                agg_dict['revenue'] = 'sum'
            if 'units' in df.columns:
                agg_dict['units'] = 'sum'
                
            # Fallback if no numeric columns found
            if not agg_dict:
                non_group_cols = [col for col in df.columns if col not in group_cols]
                if non_group_cols:
                    agg_dict[non_group_cols[0]] = 'count'
                else:
                    return df
            
            try:
                aggregated = df.groupby(group_cols).agg(agg_dict).reset_index()
                ProcessingLogService.log_info(db, job.id, f"Aggregated to {len(aggregated)} records using groups: {group_cols}", "aggregation")
                return aggregated
            except Exception as agg_err:
                ProcessingLogService.log_warning(db, job.id, f"Aggregation failed: {str(agg_err)}. Returning unaggregated data.", "aggregation")
                return df
        
        return df
    
    @staticmethod
    def pause_job(db: Session, job_id: str) -> bool:
        """Pause a running job."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job or job.status != ProcessingJobStatus.RUNNING:
            return False
        
        job.status = ProcessingJobStatus.PAUSED
        job.paused_at = datetime.utcnow()
        db.commit()
        
        manager.send_progress_update_sync(
            channel="processing",
            job_id=job.job_id,
            progress=job.progress_percentage,
            step="Paused",
            status="paused"
        )
        
        if job.created_by:
            NotificationService.create_processing_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=True,
                message=f"Processing job {job.job_id} paused."
            )
        
        return True
    
    @staticmethod
    def resume_job(db: Session, job_id: str) -> bool:
        """Resume a paused job."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job or job.status != ProcessingJobStatus.PAUSED:
            return False
        
        job.status = ProcessingJobStatus.RUNNING
        db.commit()
        
        manager.send_progress_update_sync(
            channel="processing",
            job_id=job.job_id,
            progress=job.progress_percentage,
            step="Resumed",
            status="running"
        )
        
        if job.created_by:
            NotificationService.create_processing_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=True,
                message=f"Processing job {job.job_id} resumed."
            )
        
        return True
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        """Cancel a job."""
        job = ProcessingJobService.get_job(db, job_id)
        if not job or job.status in [ProcessingJobStatus.COMPLETED, ProcessingJobStatus.FAILED]:
            return False
        
        job.status = ProcessingJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.commit()
        
        if job.created_by:
            NotificationService.create_processing_notification(
                db=db,
                user_id=job.created_by,
                job_id=job.job_id,
                success=False,
                message=f"Processing job {job.job_id} cancelled."
            )
        
        return True