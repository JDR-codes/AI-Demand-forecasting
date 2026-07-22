#fastapi_app/services/recommendation/recommendation_result_service.py
"""
Recommendation Result Service - CRUD operations for recommendations.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_
from datetime import datetime

from fastapi_app.models.recommendation_result_model import (
    RecommendationResult,
    RecommendationResultStatus,
    RecommendationResultPriority,
    RecommendationResultType,
    RecommendationResultCategory
)
from fastapi_app.models.recommendation_history_model import RecommendationHistory


class RecommendationResultService:
    """Service for managing recommendation results."""
    
    # ============= CRUD Operations =============
    
    @staticmethod
    def get_by_id(db: Session, recommendation_id: int) -> Optional[RecommendationResult]:
        """Get a specific recommendation by ID."""
        return db.query(RecommendationResult).filter(
            RecommendationResult.id == recommendation_id
        ).first()
    
    @staticmethod
    def get_by_job(db: Session, job_id: int) -> List[RecommendationResult]:
        """Get all recommendations for a job."""
        return db.query(RecommendationResult).filter(
            RecommendationResult.recommendation_job_id == job_id
        ).order_by(desc(RecommendationResult.created_at)).all()
    
    @staticmethod
    def get_by_forecast_job(db: Session, forecast_job_id: str) -> List[RecommendationResult]:
        """Get all recommendations for a forecast job."""
        return db.query(RecommendationResult).filter(
            RecommendationResult.forecast_job_id == forecast_job_id
        ).order_by(desc(RecommendationResult.created_at)).all()
    
    @staticmethod
    def get_pending(db: Session, limit: int = 100, offset: int = 0) -> List[RecommendationResult]:
        """Get pending recommendations."""
        return db.query(RecommendationResult).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).order_by(
            desc(RecommendationResult.priority),
            desc(RecommendationResult.recommendation_score),
            desc(RecommendationResult.created_at)
        ).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_by_status(
        db: Session,
        status: RecommendationResultStatus,
        limit: int = 100
    ) -> List[RecommendationResult]:
        """Get recommendations by status."""
        return db.query(RecommendationResult).filter(
            RecommendationResult.status == status
        ).order_by(desc(RecommendationResult.created_at)).limit(limit).all()
    
    @staticmethod
    def get_critical(db: Session) -> List[RecommendationResult]:
        """Get critical priority recommendations."""
        return db.query(RecommendationResult).filter(
            RecommendationResult.priority == RecommendationResultPriority.CRITICAL,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).order_by(desc(RecommendationResult.created_at)).all()
    
    @staticmethod
    def get_high(db: Session) -> List[RecommendationResult]:
        """Get high priority recommendations."""
        return db.query(RecommendationResult).filter(
            RecommendationResult.priority == RecommendationResultPriority.HIGH,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).order_by(desc(RecommendationResult.created_at)).all()
    
    @staticmethod
    def get_filtered_recommendations(
        db: Session,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        recommendation_type: Optional[str] = None,
        category: Optional[str] = None,
        sku: Optional[str] = None,
        warehouse: Optional[str] = None,
        region: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get recommendations with filters and pagination."""
        query = db.query(RecommendationResult)
        
        # Apply filters
        if status:
            try:
                query = query.filter(RecommendationResult.status == RecommendationResultStatus(status))
            except ValueError:
                pass
        
        if priority:
            try:
                query = query.filter(RecommendationResult.priority == RecommendationResultPriority(priority))
            except ValueError:
                pass
        
        if recommendation_type:
            try:
                query = query.filter(RecommendationResult.recommendation_type == RecommendationResultType(recommendation_type))
            except ValueError:
                pass
        
        if category:
            try:
                query = query.filter(RecommendationResult.category == RecommendationResultCategory(category))
            except ValueError:
                pass
        
        if sku:
            query = query.filter(RecommendationResult.sku.ilike(f"%{sku}%"))
        
        if warehouse:
            query = query.filter(RecommendationResult.warehouse.ilike(f"%{warehouse}%"))
        
        if region:
            query = query.filter(RecommendationResult.region.ilike(f"%{region}%"))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    RecommendationResult.sku.ilike(search_term),
                    RecommendationResult.title.ilike(search_term),
                    RecommendationResult.description.ilike(search_term),
                    RecommendationResult.supplier_name.ilike(search_term)
                )
            )
        
        # Default: show pending only
        if not status:
            query = query.filter(RecommendationResult.status == RecommendationResultStatus.PENDING)
        
        total = query.count()
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit
        
        # Order by priority, score, then created_at
        items = query.order_by(
            desc(RecommendationResult.priority),
            desc(RecommendationResult.recommendation_score),
            desc(RecommendationResult.created_at)
        ).offset(offset).limit(limit).all()
        
        return {
            "page": page,
            "pages": pages,
            "total": total,
            "limit": limit,
            "items": items
        }
    
    # ============= Action Methods =============
    
    @staticmethod
    def execute(
        db: Session,
        recommendation_id: int,
        user_id: int = None,
        notes: str = None
    ) -> Optional[RecommendationResult]:
        """Execute a recommendation."""
        rec = RecommendationResultService.get_by_id(db, recommendation_id)
        if not rec or rec.status != RecommendationResultStatus.PENDING:
            return None
        
        # Record history
        history = RecommendationHistory(
            recommendation_id=rec.id,
            recommendation_job_id=rec.recommendation_job_id,
            action="executed",
            previous_status=rec.status.value,
            new_status=RecommendationResultStatus.EXECUTED.value,
            performed_by=user_id,
            estimated_savings=rec.estimated_savings,
            ai_confidence=rec.ai_confidence,
            recommendation_score=rec.recommendation_score,
            forecast_value=rec.forecast_value
        )
        db.add(history)
        
        # Update recommendation
        rec.status = RecommendationResultStatus.EXECUTED
        rec.executed_by = user_id
        rec.executed_at = datetime.utcnow()
        rec.execution_notes = notes
        rec.execution_status = "completed"
        rec.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(rec)
        return rec
    
    @staticmethod
    def ignore(
        db: Session,
        recommendation_id: int,
        user_id: int = None,
        reason: str = None
    ) -> Optional[RecommendationResult]:
        """Ignore a recommendation."""
        rec = RecommendationResultService.get_by_id(db, recommendation_id)
        if not rec or rec.status != RecommendationResultStatus.PENDING:
            return None
        
        # Record history
        history = RecommendationHistory(
            recommendation_id=rec.id,
            recommendation_job_id=rec.recommendation_job_id,
            action="ignored",
            previous_status=rec.status.value,
            new_status=RecommendationResultStatus.IGNORED.value,
            performed_by=user_id,
            reason=reason,
            estimated_savings=rec.estimated_savings,
            ai_confidence=rec.ai_confidence,
            recommendation_score=rec.recommendation_score,
            forecast_value=rec.forecast_value
        )
        db.add(history)
        
        # Update recommendation
        rec.status = RecommendationResultStatus.IGNORED
        rec.ignored_by = user_id
        rec.ignored_at = datetime.utcnow()
        rec.ignored_reason = reason
        rec.execution_status = "ignored"
        rec.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(rec)
        return rec
    
    @staticmethod
    def delete(db: Session, recommendation_id: int, user_id: int = None) -> bool:
        """Soft delete a recommendation."""
        rec = RecommendationResultService.get_by_id(db, recommendation_id)
        if not rec:
            return False
        
        # Record history
        history = RecommendationHistory(
            recommendation_id=rec.id,
            recommendation_job_id=rec.recommendation_job_id,
            action="deleted",
            previous_status=rec.status.value,
            new_status="deleted",
            performed_by=user_id,
            estimated_savings=rec.estimated_savings,
            ai_confidence=rec.ai_confidence,
            recommendation_score=rec.recommendation_score,
            forecast_value=rec.forecast_value
        )
        db.add(history)
        
        # Hard delete (or could be soft delete with a deleted flag)
        db.delete(rec)
        db.commit()
        return True
    
    # ============= Bulk Actions =============
    
    @staticmethod
    def execute_all(
        db: Session,
        recommendation_ids: List[int],
        user_id: int = None
    ) -> Dict[str, Any]:
        """Execute multiple recommendations."""
        success_count = 0
        failed_count = 0
        total_savings = 0
        
        for rec_id in recommendation_ids:
            rec = RecommendationResultService.execute(db, rec_id, user_id)
            if rec:
                success_count += 1
                if rec.estimated_savings:
                    total_savings += rec.estimated_savings
            else:
                failed_count += 1
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(recommendation_ids),
            "total_savings": round(total_savings, 2),
            "message": f"Executed {success_count} recommendations"
        }
    
    @staticmethod
    def ignore_all(
        db: Session,
        recommendation_ids: List[int],
        user_id: int = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """Ignore multiple recommendations."""
        success_count = 0
        failed_count = 0
        
        for rec_id in recommendation_ids:
            rec = RecommendationResultService.ignore(db, rec_id, user_id, reason)
            if rec:
                success_count += 1
            else:
                failed_count += 1
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(recommendation_ids),
            "message": f"Ignored {success_count} recommendations"
        }
    
    @staticmethod
    def get_ids_by_filter(db: Session, filter_type: str) -> List[int]:
        """Get recommendation IDs by filter type."""
        if filter_type == "all":
            recs = RecommendationResultService.get_pending(db, 1000, 0)
        elif filter_type == "critical":
            recs = RecommendationResultService.get_critical(db)
        elif filter_type == "high":
            recs = RecommendationResultService.get_high(db)
        elif filter_type == "reorder":
            recs = db.query(RecommendationResult).filter(
                RecommendationResult.recommendation_type == RecommendationResultType.REORDER,
                RecommendationResult.status == RecommendationResultStatus.PENDING
            ).all()
        elif filter_type == "procurement":
            recs = db.query(RecommendationResult).filter(
                RecommendationResult.recommendation_type == RecommendationResultType.PROCUREMENT,
                RecommendationResult.status == RecommendationResultStatus.PENDING
            ).all()
        else:
            return []
        
        return [r.id for r in recs]
    
    @staticmethod
    def get_summary_for_filter(db: Session, filter_type: str) -> Dict[str, Any]:
        """Get summary for execute dialog."""
        ids = RecommendationResultService.get_ids_by_filter(db, filter_type)
        if not ids:
            return {
                "total_recommendations": 0,
                "categories": {},
                "estimated_savings": 0,
                "critical_actions": 0,
                "average_confidence": 0,
                "by_priority": {}
            }
        
        recs = db.query(RecommendationResult).filter(RecommendationResult.id.in_(ids)).all()
        
        categories = {}
        by_priority = {}
        total_savings = 0
        total_confidence = 0
        critical_count = 0
        
        for rec in recs:
            cat = rec.category.value if hasattr(rec.category, 'value') else str(rec.category)
            categories[cat] = categories.get(cat, 0) + 1
            
            priority = rec.priority.value if hasattr(rec.priority, 'value') else str(rec.priority)
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            if rec.estimated_savings:
                total_savings += rec.estimated_savings
            if rec.ai_confidence:
                total_confidence += rec.ai_confidence
            
            if rec.priority == RecommendationResultPriority.CRITICAL:
                critical_count += 1
        
        avg_confidence = total_confidence / len(recs) if recs else 0
        
        return {
            "total_recommendations": len(recs),
            "categories": categories,
            "estimated_savings": round(total_savings, 2),
            "critical_actions": critical_count,
            "average_confidence": round(avg_confidence, 1),
            "by_priority": by_priority
        }