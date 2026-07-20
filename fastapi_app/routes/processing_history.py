#fastapi_app/routes/processing_history.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.processing_job_model import ProcessingJob

router = APIRouter(prefix="/api/processing/history", tags=["Processing History"])


@router.get("/")
def get_processing_history(
    search: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = Query("-created_at"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get processing history with search, filters, and pagination."""
    query = db.query(ProcessingJob)
    
    if search:
        query = query.filter(
            or_(
                ProcessingJob.dataset_path.contains(search),
                ProcessingJob.job_id.contains(search)
            )
        )
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    # Sort
    sort_field = sort.lstrip('-')
    if sort.startswith('-'):
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(sort_field)
    
    total = query.count()
    offset = (page - 1) * limit
    jobs = query.offset(offset).limit(limit).all()
    
    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "status": j.status.value if hasattr(j.status, 'value') else str(j.status),
                "progress": j.progress_percentage,
                "records_loaded": j.records_loaded,
                "records_processed": j.records_processed,
                "duration_seconds": j.duration_seconds,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "dataset": j.dataset_path,
                "created_by": j.creator.name if j.creator else "System"
            }
            for j in jobs
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }