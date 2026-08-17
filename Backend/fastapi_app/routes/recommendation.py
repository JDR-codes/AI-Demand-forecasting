# fastapi_app/routes/recommendation.py - Updated to use new generator
"""
Recommendation Router - Simplified endpoints for Figma.
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
from fastapi_app.models.forecast_job_model import ForecastJob
from fastapi_app.models.forecast_job_model import ForecastResult
from fastapi_app.services.recommendation.recommendation_result_service import RecommendationResultService
from fastapi_app.services.recommendation.recommendation_dashboard_service import RecommendationDashboardService
from fastapi_app.services.recommendation.recommendation_history_service import RecommendationHistoryService
from fastapi_app.services.recommendation.recommendation_analysis_service import RecommendationAnalysisService
from fastapi_app.services.recommendation.recommendation_generator_service import RecommendationGeneratorService
from fastapi_app.services.forecast.forecast_result_service import ForecastResultService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.schemas.recommendation_schema import (
    GenerateRecommendationsRequest,
    GenerateRecommendationsResponse,
    IgnoreRequest,
    ExecuteRequest,
    BulkActionResponse
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


# ============================================================================
# GENERATE
# ============================================================================

@router.post("/generate", response_model=GenerateRecommendationsResponse)
def generate_recommendations(
    request: GenerateRecommendationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate recommendations from a completed forecast.
    This is the main entry point - no background jobs.
    """
    forecast_job_id = request.forecast_job_id
    
    # Get forecast job
    forecast_job = db.query(ForecastJob).filter(
        ForecastJob.job_id == forecast_job_id
    ).first()
    
    if not forecast_job:
        raise HTTPException(status_code=404, detail="Forecast job not found")
    
    if forecast_job.status != "completed":
        raise HTTPException(status_code=400, detail="Forecast job is not completed")
    
    # Check if recommendations already exist
    existing = db.query(RecommendationResult).filter(
        RecommendationResult.forecast_job_id == forecast_job_id
    ).first()
    
    if existing:
        # Return existing recommendations
        recs = RecommendationResultService.get_by_forecast_job(db, forecast_job_id)
        return GenerateRecommendationsResponse(
            success=True,
            message=f"Recommendations already exist for this forecast",
            count=len(recs),
            recommendations=recs
        )
    
    # Get forecast results
    results = db.query(ForecastResult).filter(
        ForecastResult.forecast_job_id == forecast_job.id,
        ForecastResult.is_forecast == True
    ).order_by(ForecastResult.forecast_date).all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No forecast results found")
    
    # Get forecast summary
    summary = ForecastResultService.get_summary(db, forecast_job_id)
    if "error" in summary:
        raise HTTPException(status_code=400, detail=summary["error"])
    
    predictions = [r.prediction for r in results]
    dates = [r.forecast_date for r in results]
    
    # 1. Analyze demand
    demand_analysis = RecommendationAnalysisService.analyze_demand(
        predictions=predictions,
        dates=dates,
        sku=forecast_job.sku,
        region=forecast_job.region,
        warehouse=forecast_job.warehouse,
        forecast_summary=summary
    )
    
    # 2. Analyze inventory
    inventory_analysis = RecommendationAnalysisService.analyze_inventory(demand_analysis)
    
    # 3. Analyze risk
    risk_analysis = RecommendationAnalysisService.analyze_risk(demand_analysis)
    
    # Combine analysis for the generator
    analysis = {
        **demand_analysis,
        "inventory": inventory_analysis,
        "risk": risk_analysis
    }
    
    # 4. Generate recommendations
    result_data = [{
        "date": r.forecast_date,
        "prediction": r.prediction,
        "confidence_score": r.confidence_score,
        "is_peak": r.is_peak,
        "sku": r.sku,
        "region": r.region,
        "warehouse": r.warehouse
    } for r in results]
    
    recommendations = RecommendationGeneratorService.generate_recommendations(
        analysis=analysis,
        forecast_results=result_data,
        sku=forecast_job.sku,
        region=forecast_job.region,
        warehouse=forecast_job.warehouse,
        user_id=current_user.id,
        forecast_summary=summary
    )
    
    if not recommendations:
        return GenerateRecommendationsResponse(
            success=True,
            message="No recommendations generated",
            count=0,
            recommendations=[]
        )
    
    # 5. Save to database
    saved = RecommendationResultService.save_recommendations(
        db=db,
        recommendations=recommendations,
        forecast_job_id=forecast_job_id
    )
    
    # 6. Send notifications for critical and high
    for rec in saved:
        if rec.priority.value in ["critical", "high"]:
            NotificationService.create_recommendation_notification(
                db=db,
                user_id=current_user.id,
                success=True,
                count=1,
                message=f"Recommendation for {rec.sku}: {rec.action_label or 'Take action'}"
            )
    
    # 7. Send dashboard refresh via WebSocket
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            manager.send_dashboard_update({
                "type": "recommendation_generated",
                "forecast_job_id": forecast_job_id,
                "count": len(saved),
                "timestamp": datetime.utcnow().isoformat()
            })
        )
    except RuntimeError:
        pass
    
    return GenerateRecommendationsResponse(
        success=True,
        message=f"Generated {len(saved)} recommendations",
        count=len(saved),
        recommendations=saved
    )


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
    filter_type: str = Query("all", description="all, critical, high, medium, reorder, procurement"),
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
    request: ExecuteRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a recommendation."""
    notes = request.notes if request else None
    
    rec = RecommendationResultService.execute(db, recommendation_id, current_user.id, notes)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")
    
    # Send notification
    NotificationService.create_recommendation_notification(
        db=db,
        user_id=current_user.id,
        success=True,
        count=1,
        message=f"✅ Recommendation executed for {rec.sku}"
    )
    
    # WebSocket update
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            manager.send_dashboard_update({
                "type": "recommendation_executed",
                "id": rec.id,
                "sku": rec.sku,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
    except RuntimeError:
        pass
    
    return rec


@router.post("/{recommendation_id}/ignore")
def ignore_recommendation(
    recommendation_id: int,
    request: IgnoreRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ignore a recommendation."""
    reason = request.reason if request else None
    
    rec = RecommendationResultService.ignore(db, recommendation_id, current_user.id, reason)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")
    
    # Send notification
    NotificationService.create_recommendation_notification(
        db=db,
        user_id=current_user.id,
        success=False,
        count=1,
        message=f"❌ Recommendation ignored for {rec.sku}"
    )
    
    return rec



# ============================================================================
# BULK ACTIONS
# ============================================================================

@router.post("/execute-all")
def execute_all(
    filter_type: str = Query("all", description="all, critical, high, medium, reorder, procurement"),
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
        NotificationService.create_recommendation_notification(
            db=db,
            user_id=current_user.id,
            success=True,
            count=result["success_count"],
            message=f"✅ Executed {result['success_count']} recommendations"
        )
    
    return result


@router.post("/ignore-all")
def ignore_all(
    filter_type: str = Query("all", description="all, critical, high, medium, reorder, procurement"),
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
        NotificationService.create_recommendation_notification(
            db=db,
            user_id=current_user.id,
            success=False,
            count=result["success_count"],
            message=f"❌ Ignored {result['success_count']} recommendations"
        )
    
    return result


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