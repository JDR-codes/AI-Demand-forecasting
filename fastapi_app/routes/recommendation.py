# fastapi_app/routes/recommendation.py - Updated to use new generator
"""
Recommendation Router - Single unified router for all recommendation endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.recommendation_result_model import (
    RecommendationResult,
    RecommendationResultStatus
)
from fastapi_app.models.recommendation_job_model import RecommendationJob
from fastapi_app.services.recommendation.recommendation_result_service import RecommendationResultService
from fastapi_app.services.recommendation.recommendation_dashboard_service import RecommendationDashboardService
from fastapi_app.services.recommendation.recommendation_history_service import RecommendationHistoryService
from fastapi_app.services.recommendation.recommendation_execution_service import RecommendationExecutionService
from fastapi_app.services.recommendation.recommendation_job_service import RecommendationJobService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.notifications.notification_service import NotificationService

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


# ============================================================================
# JOBS
# ============================================================================

@router.post("/jobs/from-forecast/{forecast_job_id}")
def create_job_from_forecast(
    forecast_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a recommendation job from a forecast."""
    job = RecommendationExecutionService.start_job_from_forecast(
        db=db,
        forecast_job_id=forecast_job_id
    )
    if not job:
        raise HTTPException(status_code=400, detail="Could not create recommendation job")
    return job


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List recommendation jobs."""
    jobs = RecommendationJobService.get_jobs(db, status, limit, offset)
    return {"items": jobs, "total": len(jobs), "limit": limit, "offset": offset}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific job."""
    job = RecommendationJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/status")
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get job status with progress."""
    status = RecommendationExecutionService.get_live_status(db, job_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.post("/jobs/{job_id}/pause")
def pause_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a running job."""
    if not RecommendationExecutionService.pause_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be paused")
    return {"message": "Job paused"}


@router.post("/jobs/{job_id}/resume")
def resume_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused job."""
    if not RecommendationExecutionService.resume_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be resumed")
    return {"message": "Job resumed"}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a job."""
    if not RecommendationExecutionService.cancel_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return {"message": "Job cancelled"}


@router.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a failed job."""
    job = RecommendationExecutionService.retry_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job retried", "new_job_id": job.job_id}


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recommendation dashboard statistics."""
    return RecommendationDashboardService.get_dashboard_stats(db)


@router.get("/dashboard/trend")
def get_trend_data(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trend data for charts."""
    return RecommendationDashboardService.get_trend_data(db, days)


# ============================================================================
# SUMMARY
# ============================================================================

@router.get("/summary")
def get_summary(
    filter_type: str = Query("all", description="all, critical, high, reorder, procurement"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary for execute dialog."""
    return RecommendationResultService.get_summary_for_filter(db, filter_type)


# ============================================================================
# RECOMMENDATIONS (CRUD)
# ============================================================================

@router.get("/")
def list_recommendations(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    recommendation_type: Optional[str] = None,
    category: Optional[str] = None,
    sku: Optional[str] = None,
    warehouse: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List recommendations with filters and pagination."""
    return RecommendationResultService.get_filtered_recommendations(
        db=db,
        status=status,
        priority=priority,
        recommendation_type=recommendation_type,
        category=category,
        sku=sku,
        warehouse=warehouse,
        region=region,
        search=search,
        page=page,
        limit=limit
    )


@router.get("/critical")
def get_critical(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get critical priority recommendations."""
    recs = RecommendationResultService.get_critical(db)
    return {"total": len(recs), "recommendations": recs}


@router.get("/high")
def get_high(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get high priority recommendations."""
    recs = RecommendationResultService.get_high(db)
    return {"total": len(recs), "recommendations": recs}


@router.get("/pending")
def get_pending(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending recommendations."""
    offset = (page - 1) * limit
    recs = RecommendationResultService.get_pending(db, limit, offset)
    total = db.query(RecommendationResult).filter(
        RecommendationResult.status == RecommendationResultStatus.PENDING
    ).count()
    return {
        "page": page,
        "pages": (total + limit - 1) // limit,
        "total": total,
        "limit": limit,
        "items": recs
    }


@router.get("/executed")
def get_executed(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get executed recommendations."""
    recs = RecommendationResultService.get_by_status(db, RecommendationResultStatus.EXECUTED, limit)
    return {"total": len(recs), "recommendations": recs}


@router.get("/ignored")
def get_ignored(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ignored recommendations."""
    recs = RecommendationResultService.get_by_status(db, RecommendationResultStatus.IGNORED, limit)
    return {"total": len(recs), "recommendations": recs}


@router.get("/{recommendation_id}")
def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific recommendation with details."""
    rec = RecommendationResultService.get_by_id(db, recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Get history
    history = RecommendationHistoryService.get_by_recommendation(db, recommendation_id)
    
    return {
        **rec.__dict__,
        "history": history
    }


# ============================================================================
# ACTIONS
# ============================================================================

@router.post("/{recommendation_id}/execute")
def execute_recommendation(
    recommendation_id: int,
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a recommendation."""
    rec = RecommendationResultService.execute(db, recommendation_id, current_user.id, notes)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")
    
    # Send notification
    NotificationService.create_notification(
        db=db,
        user_id=current_user.id,
        title=f"✅ Recommendation Executed: {rec.sku}",
        message=f"Recommendation for {rec.sku} executed successfully.",
        notification_type="recommendation_executed",
        priority="info"
    )
    
    # WebSocket update
    import asyncio
    asyncio.create_task(
        manager.send_recommendation_update({
            "type": "recommendation_executed",
            "id": rec.id,
            "sku": rec.sku,
            "timestamp": datetime.utcnow().isoformat()
        })
    )
    
    return rec


@router.post("/{recommendation_id}/ignore")
def ignore_recommendation(
    recommendation_id: int,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ignore a recommendation."""
    rec = RecommendationResultService.ignore(db, recommendation_id, current_user.id, reason)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")
    
    # Send notification
    NotificationService.create_notification(
        db=db,
        user_id=current_user.id,
        title=f"❌ Recommendation Ignored: {rec.sku}",
        message=f"Recommendation for {rec.sku} was ignored. Reason: {reason or 'Not specified'}",
        notification_type="recommendation_ignored",
        priority="info"
    )
    
    return rec


@router.delete("/{recommendation_id}")
def delete_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a recommendation."""
    success = RecommendationResultService.delete(db, recommendation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {"message": "Recommendation deleted successfully"}


# ============================================================================
# BULK ACTIONS
# ============================================================================

@router.post("/execute-all")
def execute_all(
    filter_type: str = Query("all", description="all, critical, high, reorder, procurement"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute all recommendations by filter."""
    ids = RecommendationResultService.get_ids_by_filter(db, filter_type)
    if not ids:
        return {
            "success_count": 0,
            "failed_count": 0,
            "total": 0,
            "total_savings": 0,
            "message": "No recommendations found"
        }
    
    result = RecommendationResultService.execute_all(db, ids, current_user.id)
    
    if result["success_count"] > 0:
        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            title=f"✅ Bulk Execute Completed",
            message=f"Executed {result['success_count']} recommendations",
            notification_type="recommendation_bulk",
            priority="info"
        )
    
    return result


@router.post("/ignore-all")
def ignore_all(
    filter_type: str = Query("all", description="all, critical, high, reorder, procurement"),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ignore all recommendations by filter."""
    ids = RecommendationResultService.get_ids_by_filter(db, filter_type)
    if not ids:
        return {
            "success_count": 0,
            "failed_count": 0,
            "total": 0,
            "message": "No recommendations found"
        }
    
    result = RecommendationResultService.ignore_all(db, ids, current_user.id, reason)
    
    if result["success_count"] > 0:
        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            title=f"❌ Bulk Ignore Completed",
            message=f"Ignored {result['success_count']} recommendations",
            notification_type="recommendation_bulk",
            priority="info"
        )
    
    return result


# ============================================================================
# HISTORY
# ============================================================================

@router.get("/history")
def get_history(
    recommendation_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recommendation history."""
    return RecommendationHistoryService.get_history(db, recommendation_id, action, limit, offset)


# ============================================================================
# FORECAST RECOMMENDATIONS
# ============================================================================

@router.get("/forecast/{forecast_job_id}")
def get_forecast_recommendations(
    forecast_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recommendations for a specific forecast."""
    recs = RecommendationResultService.get_by_forecast_job(db, forecast_job_id)
    return {"total": len(recs), "recommendations": recs}