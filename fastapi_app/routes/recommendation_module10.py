from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import List

from fastapi_app.db.session import get_db
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.recommendation_schema import (
    RecommendationCreate,
    RecommendationUpdate,
    RecommendationResponse,
    RecommendationBulkAction,
    BulkActionResponse,
    CriticalRecommendationsResponse,
    HighRecommendationsResponse,
    ReorderRecommendationsResponse,
    ProcurementRecommendationsResponse,
)
from fastapi_app.services.recommendation.recommendation_db_service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["Recommendation Engine"])


# ============= GET ENDPOINTS =============

@router.get("", response_model=List[RecommendationResponse])
def get_all_recommendations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all recommendations"""
    recommendations = RecommendationService.get_all_recommendations(db, limit=limit, offset=skip)
    return recommendations


@router.get("/critical", response_model=CriticalRecommendationsResponse)
def get_critical_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get critical priority recommendations - Tab: Critical"""
    recommendations = RecommendationService.get_critical_recommendations(db)
    return {"total": len(recommendations), "recommendations": recommendations}


@router.get("/high", response_model=HighRecommendationsResponse)
def get_high_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get high priority recommendations - Tab: High"""
    recommendations = RecommendationService.get_high_recommendations(db)
    return {"total": len(recommendations), "recommendations": recommendations}


@router.get("/reorder", response_model=ReorderRecommendationsResponse)
def get_reorder_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reorder type recommendations - Tab: Reorder"""
    recommendations = RecommendationService.get_reorder_recommendations(db)
    return {"total": len(recommendations), "recommendations": recommendations}


@router.get("/procurement", response_model=ProcurementRecommendationsResponse)
def get_procurement_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get procurement type recommendations - Tab: Procurement"""
    recommendations = RecommendationService.get_procurement_recommendations(db)
    return {"total": len(recommendations), "recommendations": recommendations}


# ============= SINGLE ITEM ENDPOINTS =============

@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific recommendation"""
    recommendation = RecommendationService.get_recommendation_by_id(db, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


@router.post("", response_model=RecommendationResponse)
def create_recommendation(
    recommendation: RecommendationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new recommendation"""
    db_recommendation = RecommendationService.create_recommendation(db, recommendation)
    return db_recommendation


@router.put("/{recommendation_id}", response_model=RecommendationResponse)
def update_recommendation(
    recommendation_id: int,
    recommendation_update: RecommendationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing recommendation"""
    recommendation = RecommendationService.update_recommendation(db, recommendation_id, recommendation_update)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


@router.delete("/{recommendation_id}")
def delete_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a recommendation"""
    success = RecommendationService.delete_recommendation(db, recommendation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {"message": "Recommendation deleted successfully"}


# ============= ACTION ENDPOINTS =============

@router.post("/{recommendation_id}/execute", response_model=RecommendationResponse)
def execute_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute/apply a specific recommendation"""
    recommendation = RecommendationService.execute_recommendation(db, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


@router.post("/{recommendation_id}/ignore", response_model=RecommendationResponse)
def ignore_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ignore/reject a specific recommendation"""
    recommendation = RecommendationService.ignore_recommendation(db, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


# ============= BULK ACTION ENDPOINTS =============

@router.post("/execute-all", response_model=BulkActionResponse)
def execute_all_recommendations(
    bulk_action: RecommendationBulkAction = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute/apply multiple recommendations"""
    result = RecommendationService.execute_all_recommendations(db, bulk_action.recommendation_ids)
    return result


@router.post("/ignore-all", response_model=BulkActionResponse)
def ignore_all_recommendations(
    bulk_action: RecommendationBulkAction = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ignore/reject multiple recommendations"""
    result = RecommendationService.ignore_all_recommendations(db, bulk_action.recommendation_ids)
    return result


# ============= STATS ENDPOINT =============

@router.get("/stats/overview", response_model=dict)
def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recommendation statistics and overview"""
    stats = RecommendationService.get_statistics(db)
    return stats
