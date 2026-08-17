# tasks package init
from fastapi_app.tasks.celery_tasks import (
    send_otp_email_task,
    run_training_job_task,
    run_forecast_job_task,
    run_sync_job_task,
    run_processing_job_task,
    run_upload_job_task,
)
