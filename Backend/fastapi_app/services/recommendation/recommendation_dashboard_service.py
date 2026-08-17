#fastapi_app/services/recommendation/recommendation_dashboard_service.py
"""
Recommendation Dashboard Service - Aggregates data for the dashboard.
Only returns data visible in Figma dashboard cards.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from fastapi_app.models.recommendation_result_model import (
    RecommendationResult,
    RecommendationResultStatus,
    RecommendationResultPriority,
    RecommendationResultType
)


class RecommendationDashboardService:
    """Service for recommendation dashboard data."""
    
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict[str, Any]:
        """Get dashboard statistics shown in Figma."""
        # Core counts
        total = db.query(func.count(RecommendationResult.id)).scalar() or 0
        pending = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        executed = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.status == RecommendationResultStatus.EXECUTED
        ).scalar() or 0
        ignored = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.status == RecommendationResultStatus.IGNORED
        ).scalar() or 0
        
        # Priority counts
        critical = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.priority == RecommendationResultPriority.CRITICAL,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        
        high = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.priority == RecommendationResultPriority.HIGH,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0

        medium = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.priority == RecommendationResultPriority.MEDIUM,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        
        low = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.priority == RecommendationResultPriority.LOW,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        
        # Reorder and Procurement counts
        reorder = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.recommendation_type == RecommendationResultType.REORDER,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        
        procurement = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.recommendation_type == RecommendationResultType.PROCUREMENT,
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        
        # Total savings
        total_savings = db.query(func.sum(RecommendationResult.estimated_savings)).filter(
            RecommendationResult.status == RecommendationResultStatus.EXECUTED
        ).scalar() or 0
        
        # Average confidence
        avg_confidence = db.query(func.avg(RecommendationResult.ai_confidence)).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        
        # Priority breakdown
        priority_counts = db.query(
            RecommendationResult.priority,
            func.count(RecommendationResult.id)
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).group_by(RecommendationResult.priority).all()
        
        # Type breakdown
        type_counts = db.query(
            RecommendationResult.recommendation_type,
            func.count(RecommendationResult.id)
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).group_by(RecommendationResult.recommendation_type).all()
        
        # Top SKUs by savings
        top_skus = db.query(
            RecommendationResult.sku,
            func.sum(RecommendationResult.estimated_savings).label('savings'),
            func.count(RecommendationResult.id).label('count')
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).group_by(RecommendationResult.sku).order_by(
            desc('savings')
        ).limit(5).all()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity = db.query(
            func.date(RecommendationResult.created_at).label('date'),
            func.count(RecommendationResult.id).label('generated'),
            func.sum(RecommendationResult.estimated_savings).label('savings')
        ).filter(
            RecommendationResult.created_at >= week_ago
        ).group_by(
            func.date(RecommendationResult.created_at)
        ).order_by(
            func.date(RecommendationResult.created_at).desc()
        ).limit(7).all()
        
        return {
            # Core counts
            "total": total,
            "pending": pending,
            "executed": executed,
            "ignored": ignored,
            
            # Priority and Type counts
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "reorder": reorder,
            "procurement": procurement,
            
            # Savings and confidence
            "total_savings": float(total_savings) if total_savings else 0,
            "average_confidence": round(float(avg_confidence), 1) if avg_confidence else 0,
            
            # Priority breakdown
            "priority_breakdown": {
                p[0].value if hasattr(p[0], 'value') else str(p[0]): p[1]
                for p in priority_counts
            },
            
            # Type breakdown
            "type_breakdown": {
                t[0].value if hasattr(t[0], 'value') else str(t[0]): t[1]
                for t in type_counts
            },
            
            # Top SKUs
            "top_skus": [
                {
                    "sku": s[0],
                    "savings": float(s[1]) if s[1] else 0,
                    "count": s[2]
                }
                for s in top_skus
            ],
            
            # Recent activity
            "recent_activity": [
                {
                    "date": str(a[0]),
                    "generated": a[1],
                    "savings": float(a[2]) if a[2] else 0
                }
                for a in recent_activity
            ],
            
            # Timestamp
            "updated_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_trend_data(db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Get trend data for charts."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily data
        daily_data = db.query(
            func.date(RecommendationResult.created_at).label('date'),
            func.count(RecommendationResult.id).label('generated'),
            func.sum(RecommendationResult.estimated_savings).label('savings')
        ).filter(
            RecommendationResult.created_at >= start_date
        ).group_by(
            func.date(RecommendationResult.created_at)
        ).order_by(
            func.date(RecommendationResult.created_at)
        ).all()
        
        # Execution data
        daily_executed = db.query(
            func.date(RecommendationResult.executed_at).label('date'),
            func.count(RecommendationResult.id).label('executed')
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.EXECUTED,
            RecommendationResult.executed_at >= start_date
        ).group_by(
            func.date(RecommendationResult.executed_at)
        ).all()
        
        # Merge data
        date_map = {}
        for item in daily_data:
            date_str = str(item[0])
            date_map[date_str] = {
                "date": date_str,
                "generated": item[1],
                "savings": float(item[2]) if item[2] else 0,
                "executed": 0
            }
        
        for item in daily_executed:
            date_str = str(item[0])
            if date_str in date_map:
                date_map[date_str]["executed"] = item[1]
            else:
                date_map[date_str] = {
                    "date": date_str,
                    "generated": 0,
                    "savings": 0,
                    "executed": item[1]
                }
        
        return sorted(date_map.values(), key=lambda x: x["date"])