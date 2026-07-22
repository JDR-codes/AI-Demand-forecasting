#fastapi_app/services/recommendation/recommendation_utils_service.py
"""
Recommendation Utilities Service - Consolidated validation, deduplication, scoring, and notifications.
"""
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from fastapi_app.services.notifications.notification_service import NotificationService


class RecommendationUtilsService:
    """Consolidated service for recommendation utilities."""
    
    # ============================================================
    # DUPLICATE DETECTION
    # ============================================================
    
    @staticmethod
    def remove_duplicates(
        recommendations: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Remove duplicate recommendations based on SKU + type."""
        if not recommendations:
            return [], 0
        
        seen = set()
        unique = []
        removed = 0
        
        for rec in recommendations:
            key = f"{rec.get('sku', 'default')}_{rec.get('recommendation_type', 'unknown')}"
            if key not in seen:
                seen.add(key)
                unique.append(rec)
            else:
                removed += 1
        
        return unique, removed
    
    @staticmethod
    def find_existing_duplicates(
        db: Session,
        recommendations: List[Dict[str, Any]]
    ) -> List[str]:
        """Find SKUs that already have pending recommendations."""
        from fastapi_app.models.recommendation_result_model import (
            RecommendationResult,
            RecommendationResultStatus
        )
        
        skus = [r.get('sku') for r in recommendations if r.get('sku')]
        if not skus:
            return []
        
        existing = db.query(RecommendationResult.sku).filter(
            RecommendationResult.sku.in_(skus),
            RecommendationResult.status == RecommendationResultStatus.PENDING
        ).all()
        
        return [e[0] for e in existing]
    
    # ============================================================
    # VALIDATION
    # ============================================================
    
    @staticmethod
    def validate_recommendations(
        recommendations: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate recommendations."""
        validated = []
        invalid = []
        
        for rec in recommendations:
            if RecommendationUtilsService._validate_single(rec):
                validated.append(rec)
            else:
                invalid.append(rec)
        
        return validated, invalid
    
    @staticmethod
    def _validate_single(recommendation: Dict[str, Any]) -> bool:
        """Validate a single recommendation."""
        # Required fields
        required_fields = [
            "sku", "title", "recommendation_type",
            "priority", "recommended_quantity"
        ]
        
        for field in required_fields:
            if not recommendation.get(field):
                return False
        
        # Quantity must be positive
        if recommendation.get("recommended_quantity", 0) <= 0:
            return False
        
        # Confidence must be in range
        confidence = recommendation.get("ai_confidence", 0)
        if confidence < 0 or confidence > 100:
            return False
        
        # Priority must be valid
        valid_priorities = ["critical", "high", "medium", "low"]
        if recommendation.get("priority") not in valid_priorities:
            return False
        
        return True
    
    # ============================================================
    # SCORING
    # ============================================================
    
    @staticmethod
    def calculate_score(recommendation: Dict[str, Any]) -> float:
        """Calculate overall recommendation score (0-100)."""
        weights = {
            "priority": 0.30,
            "confidence": 0.25,
            "savings": 0.20,
            "risk_reduction": 0.15,
            "impact": 0.10
        }
        
        scores = {}
        
        # Priority score
        priority = recommendation.get("priority", "medium")
        priority_map = {"critical": 100, "high": 80, "medium": 60, "low": 40}
        scores["priority"] = priority_map.get(priority, 50)
        
        # Confidence score
        scores["confidence"] = recommendation.get("ai_confidence", 80)
        
        # Savings score (normalized)
        savings = recommendation.get("estimated_savings", 0)
        scores["savings"] = min(100, savings / 10) if savings > 0 else 50
        
        # Risk reduction
        stockout = recommendation.get("stockout_probability", 0.2)
        scores["risk_reduction"] = (1 - stockout) * 100
        
        # Impact
        impact = recommendation.get("expected_impact", "")
        if "prevent" in impact.lower() or "critical" in impact.lower():
            scores["impact"] = 90
        elif "optimize" in impact.lower():
            scores["impact"] = 70
        else:
            scores["impact"] = 50
        
        # Weighted average
        total = sum(scores[k] * weights[k] for k in weights)
        return round(total, 1)
    
    @staticmethod
    def calculate_batch_scores(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate scores for a batch of recommendations."""
        for rec in recommendations:
            rec["recommendation_score"] = RecommendationUtilsService.calculate_score(rec)
        return recommendations
    
    # ============================================================
    # NOTIFICATIONS
    # ============================================================
    
    @staticmethod
    def send_notification(
        db: Session,
        user_id: Optional[int],
        recommendation: Dict[str, Any],
        action: str = "generated"
    ):
        """Send notification for a recommendation."""
        if not user_id:
            return
        
        priority = recommendation.get("priority", "medium")
        sku = recommendation.get("sku", "Unknown")
        title = recommendation.get("title", "Recommendation")
        action_label = recommendation.get("action_label", "Take action")
        
        if priority == "critical":
            notification_type = "recommendation_critical"
            priority_level = "critical"
            title_prefix = "🚨 CRITICAL"
        elif priority == "high":
            notification_type = "recommendation_high"
            priority_level = "high"
            title_prefix = "⚠️ HIGH PRIORITY"
        else:
            notification_type = "recommendation"
            priority_level = "info"
            title_prefix = "📋"
        
        if action == "generated":
            message = f"Recommendation for {sku}: {action_label}"
        elif action == "executed":
            message = f"✅ Recommendation executed for {sku}"
        elif action == "ignored":
            message = f"❌ Recommendation ignored for {sku}"
        else:
            message = f"Recommendation for {sku}: {action_label}"
        
        NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=f"{title_prefix} {title}",
            message=message,
            notification_type=notification_type,
            priority=priority_level
        )
    
    @staticmethod
    def send_bulk_notification(
        db: Session,
        user_id: Optional[int],
        recommendations: List[Dict[str, Any]],
        action: str = "generated"
    ):
        """Send bulk notification for multiple recommendations."""
        if not user_id or not recommendations:
            return
        
        # Only send for critical and high priority
        critical_count = sum(1 for r in recommendations if r.get("priority") == "critical")
        high_count = sum(1 for r in recommendations if r.get("priority") == "high")
        
        if critical_count > 0:
            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                title=f"🚨 {critical_count} Critical Recommendations",
                message=f"Critical action needed for {critical_count} SKUs",
                notification_type="recommendation_critical",
                priority="critical"
            )
        
        if high_count > 0:
            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                title=f"⚠️ {high_count} High Priority Recommendations",
                message=f"High priority recommendations for {high_count} SKUs",
                notification_type="recommendation_high",
                priority="high"
            )
        
        # Summary notification
        if len(recommendations) > 0:
            savings = sum(r.get("estimated_savings", 0) for r in recommendations)
            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                title=f"📋 {len(recommendations)} Recommendations {action.capitalize()}",
                message=f"Estimated total savings: ${savings:,.2f}",
                notification_type="recommendation_bulk",
                priority="info"
            )
    
    # ============================================================
    # COMPREHENSIVE PROCESSING
    # ============================================================
    
    @staticmethod
    def process_recommendations(
        db: Session,
        recommendations: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
        """
        Complete processing pipeline:
        1. Validate
        2. Remove duplicates
        3. Calculate scores
        4. Send notifications
        """
        if not recommendations:
            return [], 0, []
        
        # 1. Validate
        validated, invalid = RecommendationUtilsService.validate_recommendations(recommendations)
        
        # 2. Remove duplicates within this batch
        unique, removed = RecommendationUtilsService.remove_duplicates(validated)
        
        # 3. Check for existing duplicates in database
        existing_skus = RecommendationUtilsService.find_existing_duplicates(db, unique)
        final_recommendations = []
        skipped = 0
        
        for rec in unique:
            if rec.get('sku') in existing_skus:
                skipped += 1
                continue
            final_recommendations.append(rec)
        
        # 4. Calculate scores
        final_recommendations = RecommendationUtilsService.calculate_batch_scores(final_recommendations)
        
        # 5. Send notifications for critical and high priority
        critical_high = [r for r in final_recommendations if r.get("priority") in ["critical", "high"]]
        if critical_high:
            for rec in critical_high:
                RecommendationUtilsService.send_notification(db, user_id, rec, "generated")
        
        total_skipped = removed + skipped
        
        return final_recommendations, total_skipped, invalid