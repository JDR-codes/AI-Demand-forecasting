#fastapi_app/services/data_processing/processing_statistics_service.py
"""
Processing Statistics Service - Calculates statistics for processing jobs.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from fastapi_app.models.processing_job_model import ProcessingJob, ProcessingJobStatus


class ProcessingStatisticsService:
    """Service for processing job statistics."""
    
    @staticmethod
    def get_statistics(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get processing statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        jobs = db.query(ProcessingJob).filter(
            ProcessingJob.created_at >= start_date
        ).all()
        
        completed = [j for j in jobs if j.status == ProcessingJobStatus.COMPLETED]
        failed = [j for j in jobs if j.status == ProcessingJobStatus.FAILED]
        running = [j for j in jobs if j.status == ProcessingJobStatus.RUNNING]
        
        total_jobs = len(jobs)
        completed_count = len(completed)
        failed_count = len(failed)
        success_rate = (completed_count / total_jobs * 100) if total_jobs > 0 else 0
        
        avg_duration = sum(j.duration_seconds or 0 for j in completed) / completed_count if completed_count > 0 else 0
        avg_rows = sum(j.records_processed or 0 for j in completed) / completed_count if completed_count > 0 else 0
        
        # Fastest and slowest jobs
        fastest = None
        slowest = None
        if completed:
            sorted_jobs = sorted(completed, key=lambda j: j.duration_seconds or 0)
            fastest = sorted_jobs[0] if sorted_jobs else None
            slowest = sorted_jobs[-1] if sorted_jobs else None
        
        # Recent jobs
        recent = db.query(ProcessingJob).order_by(
            desc(ProcessingJob.created_at)
        ).limit(10).all()
        
        return {
            "total_jobs": total_jobs,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "running_count": len(running),
            "success_rate": round(success_rate, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "average_rows": round(avg_rows, 0),
            "rows_per_second": round(avg_rows / avg_duration, 2) if avg_duration > 0 else 0,
            "fastest_job": {
                "job_id": fastest.job_id,
                "duration": fastest.duration_seconds,
                "rows": fastest.records_processed
            } if fastest else None,
            "slowest_job": {
                "job_id": slowest.job_id,
                "duration": slowest.duration_seconds,
                "rows": slowest.records_processed
            } if slowest else None,
            "recent_jobs": [
                {
                    "job_id": j.job_id,
                    "status": j.status.value if hasattr(j.status, 'value') else str(j.status),
                    "duration": j.duration_seconds,
                    "rows": j.records_processed,
                    "created_at": j.created_at.isoformat() if j.created_at else None
                }
                for j in recent
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_chart_data(db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Get chart data for last N jobs."""
        jobs = db.query(ProcessingJob).order_by(
            desc(ProcessingJob.created_at)
        ).limit(30).all()
        
        return [
            {
                "job_id": j.job_id,
                "duration": j.duration_seconds,
                "rows": j.records_processed,
                "status": j.status.value if hasattr(j.status, 'value') else str(j.status),
                "created_at": j.created_at.isoformat() if j.created_at else None
            }
            for j in jobs
        ]