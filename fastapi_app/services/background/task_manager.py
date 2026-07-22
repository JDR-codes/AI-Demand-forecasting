# fastapi_app/background/task_manager.py
"""
Background task manager for async operations.
"""
from typing import Callable, Any, Dict, Optional
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import json

from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


class TaskManager:
    """Manager for background tasks."""
    
    @staticmethod
    def add_task(func: Callable, *args, **kwargs):
        """Add a task to run in background using thread pool."""
        def _run():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background task {func.__name__} failed: {str(e)}")
        
        _executor.submit(_run)
        logger.info(f"Added background task: {func.__name__}")
    
    @staticmethod
    async def add_async_task(func: Callable, *args, **kwargs):
        """Add an async task to run in background."""
        async def _run():
            try:
                await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background async task {func.__name__} failed: {str(e)}")
        
        asyncio.create_task(_run())
        logger.info(f"Added background async task: {func.__name__}")
    
    @staticmethod
    def run_sync_job(job_id: str):
        from fastapi_app.services.data_integration.sync_job_service import SyncJobService
        def _run():
            db = SessionLocal()
            try:
                SyncJobService.run_job(db, job_id)
            except Exception as e:
                logger.error(f"Sync job {job_id} failed: {str(e)}")
            finally:
                db.close()
        TaskManager.add_task(_run)
    
    @staticmethod
    def run_upload_job(job_id: str):
        from fastapi_app.services.data_integration.upload_job_service import UploadJobService
        def _run():
            db = SessionLocal()
            try:
                UploadJobService.run_job(db, job_id)
            except Exception as e:
                logger.error(f"Upload job {job_id} failed: {str(e)}")
            finally:
                db.close()
        TaskManager.add_task(_run)
    
    @staticmethod
    def run_processing_job(job_id: str):
        from fastapi_app.services.data_processing.processing_job_service import ProcessingJobService
        def _run():
            db = SessionLocal()
            try:
                ProcessingJobService.run_job(db, job_id)
            except Exception as e:
                logger.error(f"Processing job {job_id} failed: {str(e)}")
            finally:
                db.close()
        TaskManager.add_task(_run)
    
    @staticmethod
    def run_forecast_job(job_id: str):
        from fastapi_app.services.forecast.forecast_execution_service import ForecastExecutionService
        def _run():
            db = SessionLocal()
            try:
                ForecastExecutionService.run_job(db, job_id)
            except Exception as e:
                logger.error(f"Forecast job {job_id} failed: {str(e)}")
            finally:
                db.close()
        TaskManager.add_task(_run)
    
    # ============================================================
    # Recommendation Job Runner
    # ============================================================
    @staticmethod
    def run_recommendation_job(forecast_job_id: str, forecast_summary: Optional[Dict[str, Any]] = None):
        """
        Run a recommendation job in background.
        Triggered by forecast completion.
        """
        from fastapi_app.services.recommendation.recommendation_execution_service import RecommendationExecutionService
        
        def _run():
            db = SessionLocal()
            try:
                logger.info(f"Starting recommendation job for forecast {forecast_job_id}")
                
                # Pass forecast summary if available
                if forecast_summary:
                    result = RecommendationExecutionService.start_job_from_forecast(
                        db, forecast_job_id, forecast_summary
                    )
                else:
                    result = RecommendationExecutionService.start_job_from_forecast(
                        db, forecast_job_id
                    )
                
                if result:
                    logger.info(f"Recommendation job completed for forecast {forecast_job_id}")
                else:
                    logger.error(f"Recommendation job failed for forecast {forecast_job_id}")
            except Exception as e:
                logger.error(f"Recommendation job for forecast {forecast_job_id} failed: {str(e)}")
            finally:
                db.close()
        
        TaskManager.add_task(_run)
    
    @staticmethod
    def shutdown():
        _executor.shutdown(wait=True)
        logger.info("Task manager shut down")