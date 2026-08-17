#fastapi_app/services/recommendation/recommendation_history_service.py
"""
Recommendation History Service - Manages recommendation history.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta

from fastapi_app.models.recommendation_history_model import RecommendationHistory


class RecommendationHistoryService:
    """Service for recommendation history operations."""
    
    @staticmethod
    def get_history(
        db: Session,
        recommendation_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[RecommendationHistory]:
        """Get history records with filters."""
        query = db.query(RecommendationHistory)
        
        if recommendation_id:
            query = query.filter(
                RecommendationHistory.recommendation_id == recommendation_id
            )
        
        if action:
            query = query.filter(RecommendationHistory.action == action)
        
        return query.order_by(
            desc(RecommendationHistory.performed_at)
        ).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_by_recommendation(
        db: Session,
        recommendation_id: int,
        limit: int = 50
    ) -> List[RecommendationHistory]:
        """Get history for a specific recommendation."""
        return db.query(RecommendationHistory).filter(
            RecommendationHistory.recommendation_id == recommendation_id
        ).order_by(
            desc(RecommendationHistory.performed_at)
        ).limit(limit).all()
    
    @staticmethod
    def get_recent_activity(
        db: Session,
        days: int = 7,
        limit: int = 20
    ) -> List[RecommendationHistory]:
        """Get recent activity."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        return db.query(RecommendationHistory).filter(
            RecommendationHistory.performed_at >= start_date
        ).order_by(
            desc(RecommendationHistory.performed_at)
        ).limit(limit).all()
    
    @staticmethod
    def get_activity_summary(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get activity summary."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Counts by action
        action_counts = db.query(
            RecommendationHistory.action,
            func.count(RecommendationHistory.id)
        ).filter(
            RecommendationHistory.performed_at >= start_date
        ).group_by(RecommendationHistory.action).all()
        
        # Daily activity
        daily_activity = db.query(
            func.date(RecommendationHistory.performed_at).label('date'),
            func.count(RecommendationHistory.id).label('count')
        ).filter(
            RecommendationHistory.performed_at >= start_date
        ).group_by(
            func.date(RecommendationHistory.performed_at)
        ).order_by(
            func.date(RecommendationHistory.performed_at)
        ).all()
        
        return {
            "action_counts": {
                a[0]: a[1] for a in action_counts
            },
            "daily_activity": [
                {
                    "date": str(day[0]),
                    "count": day[1]
                }
                for day in daily_activity
            ],
            "period_days": days,
            "total_actions": sum(a[1] for a in action_counts)
        }