#fastapi_app/services/data_processing/processing_log_service.py

"""
Processing Log Service - Handles logging for processing jobs.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import List, Optional

from fastapi_app.models.processing_job_model import ProcessingJobLog


class ProcessingLogService:
    """Service for managing processing logs."""
    
    @staticmethod
    def log_info(db: Session, job_id: int, message: str, step: str = None):
        """Log an info message."""
        log = ProcessingJobLog(
            processing_job_id=job_id,
            level="INFO",
            message=message,
            step=step,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    
    @staticmethod
    def log_warning(db: Session, job_id: int, message: str, step: str = None):
        """Log a warning message."""
        log = ProcessingJobLog(
            processing_job_id=job_id,
            level="WARNING",
            message=message,
            step=step,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    
    @staticmethod
    def log_error(db: Session, job_id: int, message: str, step: str = None):
        """Log an error message."""
        log = ProcessingJobLog(
            processing_job_id=job_id,
            level="ERROR",
            message=message,
            step=step,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    
    @staticmethod
    def get_logs(db: Session, job_id: int, limit: int = 100) -> List[ProcessingJobLog]:
        """Get logs for a job."""
        return db.query(ProcessingJobLog).filter(
            ProcessingJobLog.processing_job_id == job_id
        ).order_by(desc(ProcessingJobLog.timestamp)).limit(limit).all()