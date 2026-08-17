# fastapi_app/background/task_manager.py
"""
Background task manager for async operations.
Uses ThreadPoolExecutor for CPU-bound tasks and asyncio for I/O-bound tasks.
"""
from typing import Callable, Any
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio

from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound background tasks
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
        """Run a sync job in background using Celery."""
        from fastapi_app.tasks.celery_tasks import run_sync_job_task
        run_sync_job_task.delay(job_id)
    
    @staticmethod
    def run_upload_job(job_id: str):
        """Run an upload job in background using Celery."""
        from fastapi_app.tasks.celery_tasks import run_upload_job_task
        run_upload_job_task.delay(job_id)
    
    @staticmethod
    def run_processing_job(job_id: str):
        """Run a processing job in background using Celery."""
        from fastapi_app.tasks.celery_tasks import run_processing_job_task
        run_processing_job_task.delay(job_id)
    
    @staticmethod
    def run_forecast_job(job_id: str):
        """Run a forecast job in background using Celery."""
        from fastapi_app.tasks.celery_tasks import run_forecast_job_task
        run_forecast_job_task.delay(job_id)
    
    @staticmethod
    def shutdown():
        """Shutdown the thread pool executor."""
        _executor.shutdown(wait=True)
        logger.info("Task manager shut down")