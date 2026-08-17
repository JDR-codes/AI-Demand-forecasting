import logging
from fastapi_app.celery_app import celery_app
from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="fastapi_app.tasks.celery_tasks.send_otp_email_task")
def send_otp_email_task(to_email: str, otp_code: str, expiry_minutes: int = 10) -> None:
    """Send an OTP email asynchronously in a worker process."""
    logger.info(f"Asynchronously sending OTP email to {to_email}")
    from fastapi_app.utils.email_utils import send_otp_email
    send_otp_email(to_email, otp_code, expiry_minutes)


@celery_app.task(name="fastapi_app.tasks.celery_tasks.run_training_job_task")
def run_training_job_task(job_id: str) -> None:
    """Execute model training asynchronously in a worker process."""
    logger.info(f"Asynchronously running training job {job_id}")
    db = SessionLocal()
    try:
        from fastapi_app.services.forecast.training_service import TrainingService
        TrainingService.run_job(db, job_id)
    except Exception as e:
        logger.error(f"Async training job {job_id} failed: {str(e)}")
    finally:
        db.close()


@celery_app.task(name="fastapi_app.tasks.celery_tasks.run_forecast_job_task")
def run_forecast_job_task(job_id: str) -> None:
    """Execute forecast generation asynchronously in a worker process."""
    logger.info(f"Asynchronously running forecast job {job_id}")
    db = SessionLocal()
    try:
        from fastapi_app.services.forecast.forecast_execution_service import ForecastExecutionService
        ForecastExecutionService.run_job(db, job_id)
    except Exception as e:
        logger.error(f"Async forecast job {job_id} failed: {str(e)}")
    finally:
        db.close()


@celery_app.task(name="fastapi_app.tasks.celery_tasks.run_sync_job_task")
def run_sync_job_task(job_id: str) -> None:
    """Execute data sync asynchronously in a worker process."""
    logger.info(f"Asynchronously running sync job {job_id}")
    db = SessionLocal()
    try:
        from fastapi_app.services.data_integration.sync_job_service import SyncJobService
        SyncJobService.run_job(db, job_id)
    except Exception as e:
        logger.error(f"Async sync job {job_id} failed: {str(e)}")
    finally:
        db.close()


@celery_app.task(name="fastapi_app.tasks.celery_tasks.run_processing_job_task")
def run_processing_job_task(job_id: str) -> None:
    """Execute data processing pipeline asynchronously in a worker process."""
    logger.info(f"Asynchronously running data processing job {job_id}")
    db = SessionLocal()
    try:
        from fastapi_app.services.data_processing.processing_job_service import ProcessingJobService
        ProcessingJobService.run_job(db, job_id)
    except Exception as e:
        logger.error(f"Async data processing job {job_id} failed: {str(e)}")
    finally:
        db.close()


@celery_app.task(name="fastapi_app.tasks.celery_tasks.run_upload_job_task")
def run_upload_job_task(job_id: str) -> None:
    """Execute data upload asynchronously in a worker process."""
    logger.info(f"Asynchronously running upload job {job_id}")
    db = SessionLocal()
    try:
        from fastapi_app.services.data_integration.upload_job_service import UploadJobService
        UploadJobService.run_job(db, job_id)
    except Exception as e:
        logger.error(f"Async upload job {job_id} failed: {str(e)}")
    finally:
        db.close()
