#fastapi_app/services/recommendation/recommendation_dashboard_service.py
"""
Recommendation Dashboard Service - Aggregates data for the Figma dashboard.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta

from fastapi_app.models.recommendation_result_model import (
    RecommendationResult,
    RecommendationResultStatus,
    RecommendationResultPriority,
    RecommendationResultType,
    RecommendationResultCategory
)
from fastapi_app.models.recommendation_history_model import RecommendationHistory


class RecommendationDashboardService:
    """Service for recommendation dashboard data."""
    
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        # Base counts
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
        
        # Today's metrics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        executed_today = db.query(func.count(RecommendationResult.id)).filter(
            RecommendationResult.status == RecommendationResultStatus.EXECUTED,
            RecommendationResult.executed_at >= today
        ).scalar() or 0
        
        today_savings = db.query(func.sum(RecommendationResult.estimated_savings)).filter(
            RecommendationResult.status == RecommendationResultStatus.EXECUTED,
            RecommendationResult.executed_at >= today
        ).scalar() or 0
        
        # Total savings
        total_savings = db.query(func.sum(RecommendationResult.estimated_savings)).filter(
            RecommendationResult.status == RecommendationResultStatus.EXECUTED
        ).scalar() or 0
        
        # Average confidence
        avg_confidence = db.query(func.avg(RecommendationResult.ai_confidence)).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).scalar() or 0
        
        # Average risk
        avg_risk = db.query(func.avg(RecommendationResult.risk_score)).filter(
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
        
        # Category breakdown
        category_counts = db.query(
            RecommendationResult.category,
            func.count(RecommendationResult.id)
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).group_by(RecommendationResult.category).all()
        
        # Warehouse breakdown
        warehouse_counts = db.query(
            RecommendationResult.warehouse,
            func.count(RecommendationResult.id)
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING,
            RecommendationResult.warehouse.isnot(None)
        ).group_by(RecommendationResult.warehouse).all()
        
        # Top warehouses
        warehouse_counts = sorted(warehouse_counts, key=lambda x: x[1], reverse=True)[:5]
        
        # Supplier breakdown
        supplier_counts = db.query(
            RecommendationResult.supplier_name,
            func.count(RecommendationResult.id)
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING,
            RecommendationResult.supplier_name.isnot(None)
        ).group_by(RecommendationResult.supplier_name).all()
        supplier_counts = sorted(supplier_counts, key=lambda x: x[1], reverse=True)[:5]
        
        # Top SKUs
        top_skus = db.query(
            RecommendationResult.sku,
            func.count(RecommendationResult.id).label('count'),
            func.sum(RecommendationResult.estimated_savings).label('savings')
        ).filter(
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).group_by(RecommendationResult.sku).order_by(
            desc('count')
        ).limit(5).all()
        
        # Execution rate
        execution_rate = (executed / total * 100) if total > 0 else 0
        
        # Recent activity (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_activity = db.query(
            func.date(RecommendationResult.created_at).label('date'),
            func.count(RecommendationResult.id).label('generated'),
            func.sum(RecommendationResult.estimated_savings).label('savings')
        ).filter(
            RecommendationResult.created_at >= day_ago
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
            "execution_rate": round(execution_rate, 1),
            
            # Today's metrics
            "executed_today": executed_today,
            "today_savings": float(today_savings) if today_savings else 0,
            "total_savings": float(total_savings) if total_savings else 0,
            
            # Confidence and risk
            "average_confidence": round(float(avg_confidence), 1) if avg_confidence else 0,
            "average_risk": round(float(avg_risk), 1) if avg_risk else 0,
            
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
            
            # Category breakdown
            "category_breakdown": {
                c[0].value if hasattr(c[0], 'value') else str(c[0]): c[1]
                for c in category_counts
            },
            
            # Warehouse breakdown
            "warehouse_breakdown": {
                w[0]: w[1] for w in warehouse_counts
            },
            
            # Supplier breakdown
            "supplier_breakdown": {
                s[0]: s[1] for s in supplier_counts
            },
            
            # Top SKUs
            "top_skus": [
                {
                    "sku": s[0],
                    "count": s[1],
                    "savings": float(s[2]) if s[2] else 0
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
            func.count(RecommendationResult.id).label('executed'),
            func.sum(RecommendationResult.estimated_savings).label('executed_savings')
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
                "executed": 0,
                "executed_savings": 0
            }
        
        for item in daily_executed:
            date_str = str(item[0])
            if date_str in date_map:
                date_map[date_str]["executed"] = item[1]
                date_map[date_str]["executed_savings"] = float(item[2]) if item[2] else 0
            else:
                date_map[date_str] = {
                    "date": date_str,
                    "generated": 0,
                    "savings": 0,
                    "executed": item[1],
                    "executed_savings": float(item[2]) if item[2] else 0
                }
        
        result = sorted(date_map.values(), key=lambda x: x["date"])
        
        # Add running totals
        running_generated = 0
        running_executed = 0
        running_savings = 0
        
        for item in result:
            running_generated += item["generated"]
            running_executed += item["executed"]
            running_savings += item["savings"]
            item["running_generated"] = running_generated
            item["running_executed"] = running_executed
            item["running_savings"] = round(running_savings, 2)
        
        return result