#fastapi_app/routes/processing_details.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.processing_job_model import (
    ProcessingJob,
    ProcessingOutlierResult,
    ProcessingGeneratedFeature,
    ProcessingJobLog
)

router = APIRouter(prefix="/api/processing/details", tags=["Processing Details"])


@router.get("/{job_id}/outliers")
def get_processing_outliers(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get outlier detection results for a processing job."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    outliers = db.query(ProcessingOutlierResult).filter(
        ProcessingOutlierResult.processing_job_id == job.id
    ).all()
    
    return {
        "job_id": job_id,
        "outliers": [
            {
                "column": o.column_name,
                "method": o.method,
                "total_outliers": o.total_outliers,
                "removed": o.removed,
                "capped": o.capped,
                "normal_values": o.normal_values,
                "percentage_removed": o.percentage_removed,
                "percentage_capped": o.percentage_capped,
                "spike_rows": o.spike_rows,
                "normal_points": o.normal_points[:20] if o.normal_points else [],
                "outlier_points": o.outlier_points[:20] if o.outlier_points else []
            }
            for o in outliers
        ],
        "total_columns": len(outliers)
    }


@router.get("/{job_id}/outliers/chart")
def get_outlier_chart(
    job_id: str,
    column: str = Query(..., description="Column name to chart"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get outlier chart data for a specific column."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    outlier = db.query(ProcessingOutlierResult).filter(
        ProcessingOutlierResult.processing_job_id == job.id,
        ProcessingOutlierResult.column_name == column
    ).first()
    
    if not outlier:
        raise HTTPException(status_code=404, detail="Outlier data not found for column")
    
    return {
        "column": column,
        "normal_points": outlier.normal_points or [],
        "outlier_points": outlier.outlier_points or [],
        "spike_rows": outlier.spike_rows or [],
        "total_outliers": outlier.total_outliers,
        "normal_count": outlier.normal_values,
        "removed": outlier.removed,
        "capped": outlier.capped
    }


@router.get("/{job_id}/features")
def get_processing_features(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get generated features for a processing job."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    features = db.query(ProcessingGeneratedFeature).filter(
        ProcessingGeneratedFeature.processing_job_id == job.id
    ).order_by(ProcessingGeneratedFeature.importance.desc()).all()
    
    # Group by type
    by_type = {}
    for f in features:
        if f.feature_type not in by_type:
            by_type[f.feature_type] = []
        by_type[f.feature_type].append({
            "name": f.name,
            "description": f.description,
            "importance": f.importance
        })
    
    return {
        "job_id": job_id,
        "total_features": len(features),
        "features": [
            {
                "name": f.name,
                "type": f.feature_type,
                "description": f.description,
                "importance": f.importance,
                "sample_data": f.data[:10] if f.data else []
            }
            for f in features
        ],
        "by_type": by_type,
        "feature_importance": {f.name: f.importance for f in features}
    }


@router.get("/{job_id}/logs")
def get_processing_logs(
    job_id: str,
    limit: int = Query(100, ge=1, le=500),
    level: str = Query(None, description="Filter by log level"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get logs for a processing job."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.job_id == job_id,
        ProcessingJob.created_by == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    query = db.query(ProcessingJobLog).filter(
        ProcessingJobLog.processing_job_id == job.id
    )
    
    if level:
        query = query.filter(ProcessingJobLog.level == level.upper())
    
    logs = query.order_by(desc(ProcessingJobLog.timestamp)).limit(limit).all()
    
    return {
        "job_id": job_id,
        "total_logs": len(logs),
        "logs": [
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "message": log.message,
                "step": log.step,
                "metadata": log.log_metadata
            }
            for log in reversed(logs)  # Chronological order
        ]
    }