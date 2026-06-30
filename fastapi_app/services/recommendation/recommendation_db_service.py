from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from fastapi_app.models.recommendation_model import Recommendation
from fastapi_app.schemas.recommendation_schema import (
    RecommendationCreate,
    RecommendationUpdate,
    RecommendationResponse,
)
from datetime import datetime
from typing import List, Optional, Dict, Any


class RecommendationService:
    """Manages all recommendation operations"""

    @staticmethod
    def create_recommendation(db: Session, recommendation: RecommendationCreate) -> Recommendation:
        """Create a new recommendation"""
        db_recommendation = Recommendation(**recommendation.dict())
        db.add(db_recommendation)
        db.commit()
        db.refresh(db_recommendation)
        return db_recommendation

    @staticmethod
    def get_all_recommendations(db: Session, limit: int = 100, offset: int = 0) -> List[Recommendation]:
        """Get all recommendations with pagination"""
        return (
            db.query(Recommendation)
            .order_by(desc(Recommendation.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recommendation_by_id(db: Session, recommendation_id: int) -> Optional[Recommendation]:
        """Get a specific recommendation"""
        return db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()

    @staticmethod
    def update_recommendation(
        db: Session, recommendation_id: int, recommendation_update: RecommendationUpdate
    ) -> Optional[Recommendation]:
        """Update an existing recommendation"""
        db_recommendation = RecommendationService.get_recommendation_by_id(db, recommendation_id)
        if db_recommendation:
            update_data = recommendation_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_recommendation, key, value)
            db_recommendation.updated_at = datetime.utcnow()
            db.add(db_recommendation)
            db.commit()
            db.refresh(db_recommendation)
        return db_recommendation

    @staticmethod
    def delete_recommendation(db: Session, recommendation_id: int) -> bool:
        """Delete a recommendation"""
        db_recommendation = RecommendationService.get_recommendation_by_id(db, recommendation_id)
        if db_recommendation:
            db.delete(db_recommendation)
            db.commit()
            return True
        return False

    # ============= Filter Methods =============

    @staticmethod
    def get_critical_recommendations(db: Session) -> List[Recommendation]:
        """Get all critical priority recommendations"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.priority == "critical")
            .order_by(desc(Recommendation.created_at))
            .all()
        )

    @staticmethod
    def get_high_recommendations(db: Session) -> List[Recommendation]:
        """Get all high priority recommendations"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.priority == "high")
            .order_by(desc(Recommendation.created_at))
            .all()
        )

    @staticmethod
    def get_reorder_recommendations(db: Session) -> List[Recommendation]:
        """Get all reorder type recommendations"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.recommendation_type == "reorder")
            .order_by(desc(Recommendation.created_at))
            .all()
        )

    @staticmethod
    def get_procurement_recommendations(db: Session) -> List[Recommendation]:
        """Get all procurement type recommendations"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.recommendation_type == "procurement")
            .order_by(desc(Recommendation.created_at))
            .all()
        )

    @staticmethod
    def get_by_priority(db: Session, priority: str) -> List[Recommendation]:
        """Get recommendations by priority"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.priority == priority)
            .order_by(desc(Recommendation.created_at))
            .all()
        )

    @staticmethod
    def get_by_type(db: Session, recommendation_type: str) -> List[Recommendation]:
        """Get recommendations by type"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.recommendation_type == recommendation_type)
            .order_by(desc(Recommendation.created_at))
            .all()
        )

    @staticmethod
    def get_pending_recommendations(db: Session) -> List[Recommendation]:
        """Get all pending recommendations"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.status == "pending")
            .order_by(desc(Recommendation.created_at))
            .all()
        )

    # ============= Action Methods =============

    @staticmethod
    def execute_recommendation(db: Session, recommendation_id: int) -> Optional[Recommendation]:
        """Execute/apply a recommendation"""
        db_recommendation = RecommendationService.get_recommendation_by_id(db, recommendation_id)
        if db_recommendation:
            db_recommendation.status = "executed"
            db_recommendation.updated_at = datetime.utcnow()
            db.add(db_recommendation)
            db.commit()
            db.refresh(db_recommendation)
        return db_recommendation

    @staticmethod
    def ignore_recommendation(db: Session, recommendation_id: int) -> Optional[Recommendation]:
        """Ignore/reject a recommendation"""
        db_recommendation = RecommendationService.get_recommendation_by_id(db, recommendation_id)
        if db_recommendation:
            db_recommendation.status = "ignored"
            db_recommendation.updated_at = datetime.utcnow()
            db.add(db_recommendation)
            db.commit()
            db.refresh(db_recommendation)
        return db_recommendation

    @staticmethod
    def execute_all_recommendations(db: Session, recommendation_ids: List[int]) -> Dict[str, Any]:
        """Execute multiple recommendations"""
        success_count = 0
        failed_count = 0

        for rec_id in recommendation_ids:
            try:
                RecommendationService.execute_recommendation(db, rec_id)
                success_count += 1
            except Exception:
                failed_count += 1

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(recommendation_ids),
            "message": f"Executed {success_count} recommendations",
        }

    @staticmethod
    def ignore_all_recommendations(db: Session, recommendation_ids: List[int]) -> Dict[str, Any]:
        """Ignore multiple recommendations"""
        success_count = 0
        failed_count = 0

        for rec_id in recommendation_ids:
            try:
                RecommendationService.ignore_recommendation(db, rec_id)
                success_count += 1
            except Exception:
                failed_count += 1

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(recommendation_ids),
            "message": f"Ignored {success_count} recommendations",
        }

    # ============= Stats Methods =============

    @staticmethod
    def get_statistics(db: Session) -> Dict[str, Any]:
        """Get recommendation statistics"""
        total = db.query(func.count(Recommendation.id)).scalar() or 0
        pending = (
            db.query(func.count(Recommendation.id))
            .filter(Recommendation.status == "pending")
            .scalar()
            or 0
        )
        executed = (
            db.query(func.count(Recommendation.id))
            .filter(Recommendation.status == "executed")
            .scalar()
            or 0
        )
        ignored = (
            db.query(func.count(Recommendation.id))
            .filter(Recommendation.status == "ignored")
            .scalar()
            or 0
        )

        # Count by priority
        priority_counts = db.query(
            Recommendation.priority,
            func.count(Recommendation.id),
        ).group_by(Recommendation.priority).all()

        # Count by type
        type_counts = db.query(
            Recommendation.recommendation_type,
            func.count(Recommendation.id),
        ).group_by(Recommendation.recommendation_type).all()

        return {
            "total": total,
            "status_breakdown": {
                "pending": pending,
                "executed": executed,
                "ignored": ignored,
            },
            "priority_breakdown": {p[0]: p[1] for p in priority_counts},
            "type_breakdown": {t[0]: t[1] for t in type_counts},
        }
