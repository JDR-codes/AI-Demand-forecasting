# fastapi_app/services/recommendation/recommendation_generator_service.py
"""
Recommendation Generator Service - Business-focused recommendation generation.
Generates actionable business recommendations from forecast analysis.
Includes validation, deduplication, and scoring.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np


class RecommendationGeneratorService:
    """Service for generating business recommendations from forecast analysis."""
    
    # ============================================================
    # MAIN GENERATION
    # ============================================================
    
    @staticmethod
    def generate_recommendations(
        analysis: Dict[str, Any],
        forecast_results: List[Dict[str, Any]],
        sku: Optional[str] = None,
        region: Optional[str] = None,
        warehouse: Optional[str] = None,
        user_id: Optional[int] = None,
        forecast_summary: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate business recommendations from forecast analysis."""
        recommendations = []
        
        # Extract key metrics
        avg_demand = analysis.get("average_demand", 0)
        max_demand = analysis.get("max_demand", 0)
        peak_days = analysis.get("peak_days", [])
        trend = analysis.get("trend", {})
        trend_direction = trend.get("direction", "stable")
        trend_strength = trend.get("strength", "weak")
        confidence_score = analysis.get("confidence_score", 80)
        demand_score = analysis.get("demand_score", 50)
        
        # Risk analysis
        risk = analysis.get("risk", {})
        overall_risk = risk.get("overall_risk", "medium")
        risk_score = risk.get("risk_score", 40)
        
        # Inventory analysis
        inventory = analysis.get("inventory", {})
        inventory_status = inventory.get("overall_status", "stable")
        safety_stock = inventory.get("safety_stock_units", avg_demand * 0.2)
        
        # Forecast summary
        forecast_accuracy = forecast_summary.get("accuracy", 85) if forecast_summary else 85
        forecast_window = forecast_summary.get("forecast_window", 7) if forecast_summary else 7
        forecast_start = forecast_summary.get("forecast_start") if forecast_summary else None
        forecast_end = forecast_summary.get("forecast_end") if forecast_summary else None
        
        # ============================================================
        # Generate recommendations based on analysis
        # ============================================================
        
        # 1. Critical Alert - High risk + low confidence
        if overall_risk == "high" and confidence_score < 60:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="critical_alert",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    max_demand=max_demand,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 2. Demand Spike - Peak days detected
        if peak_days and len(peak_days) > 0:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="demand_spike",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    max_demand=max_demand,
                    peak_days=peak_days,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 3. Demand Drop - Decreasing trend
        if trend_direction == "decreasing" and trend_strength in ["moderate", "strong"]:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="demand_drop",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    trend_direction=trend_direction,
                    trend_strength=trend_strength,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 4. Reorder - Stable demand
        if trend_direction == "stable" and avg_demand > 10:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="reorder",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    safety_stock=safety_stock,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 5. Procurement - Increasing trend
        if trend_direction == "increasing" and trend_strength in ["moderate", "strong"]:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="procurement",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    trend_direction=trend_direction,
                    trend_strength=trend_strength,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 6. Safety Stock - High variability
        if analysis.get("coefficient_variation", 0) > 0.25:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="safety_stock",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    safety_stock=safety_stock,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 7. Overstock - Decreasing trend with high inventory
        if trend_direction == "decreasing" and avg_demand > 0:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="overstock",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    trend_direction=trend_direction,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 8. Low Confidence Alert
        if confidence_score < 50:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="low_confidence_alert",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    confidence_score=confidence_score,
                    risk_score=risk_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 9. Seasonal Stock - If peaks are periodic
        if len(peak_days) > 1:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="seasonal_stock",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    peak_days=peak_days,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 10. Supplier Risk - High risk + decreasing trend
        if overall_risk == "high" and trend_direction == "decreasing":
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="supplier_risk",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    risk_score=risk_score,
                    trend_direction=trend_direction,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 11. Inventory Optimization - Always include for medium/large demand
        if avg_demand > 50:
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="inventory_optimization",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    safety_stock=safety_stock,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # 12. Bulk Purchase - High confidence + increasing trend
        if confidence_score > 80 and trend_direction == "increasing":
            recommendations.append(
                RecommendationGeneratorService._create_recommendation(
                    rec_type="bulk_purchase",
                    sku=sku,
                    region=region,
                    warehouse=warehouse,
                    avg_demand=avg_demand,
                    trend_direction=trend_direction,
                    confidence_score=confidence_score,
                    risk_score=risk_score,
                    forecast_accuracy=forecast_accuracy,
                    forecast_window=forecast_window
                )
            )
        
        # Calculate scores and validate
        recommendations = RecommendationGeneratorService._process_batch(recommendations, risk_score)
        
        return recommendations
    
    # ============================================================
    # RECOMMENDATION CREATION
    # ============================================================
    
    @staticmethod
    def _create_recommendation(
        rec_type: str,
        sku: Optional[str],
        region: Optional[str],
        warehouse: Optional[str],
        avg_demand: float,
        max_demand: float = 0,
        peak_days: List = None,
        trend_direction: str = "stable",
        trend_strength: str = "weak",
        safety_stock: float = 0,
        risk_score: float = 40,
        confidence_score: float = 80,
        forecast_accuracy: float = 85,
        forecast_window: int = 7
    ) -> Dict[str, Any]:
        """Create a recommendation with all required fields."""
        
        peak_days = peak_days or []
        sku = sku or "default"
        region = region or "default"
        warehouse = warehouse or "default"
        
        configs = {
            "critical_alert": {
                "title": f"🚨 CRITICAL ALERT - SKU {sku}",
                "description": f"High risk detected with low confidence ({confidence_score:.0f}%). Immediate action required.",
                "category": "risk_management",
                "priority": "critical",
                "action_label": "Review forecast and inventory immediately",
                "business_reason": "High business risk due to forecast uncertainty",
                "expected_impact": "Prevent potential stockout or overstock",
                "estimated_savings": round(avg_demand * 50, 2),
                "recommended_quantity": int(avg_demand * 1.5),
                "stockout_probability": 0.45
            },
            "demand_spike": {
                "title": f"📈 DEMALL SPIKE - SKU {sku}", # Keep as in source file or fix it? Let's use source file spelling f"📈 DEMAND SPIKE - SKU {sku}" which was "📈 DEMAND SPIKE - SKU {sku}" in view output
                "title": f"📈 DEMAND SPIKE - SKU {sku}",
                "description": f"Peak demand detected: {len(peak_days)} days exceeding threshold. Peak value: {max_demand:.0f} units.",
                "category": "demand_management",
                "priority": "high" if len(peak_days) > 3 else "medium",
                "action_label": f"Increase stock to {int(max_demand * 1.3)} units",
                "business_reason": "Demand significantly above average",
                "expected_impact": "Meet peak demand and prevent stockout",
                "estimated_savings": round(max_demand * 30, 2),
                "recommended_quantity": int(max_demand * 1.3),
                "stockout_probability": 0.35
            },
            "demand_drop": {
                "title": f"📉 DEMAND DROP - SKU {sku}",
                "description": f"Demand decreasing {trend_strength}. Reduce inventory to prevent overstock.",
                "category": "inventory_optimization",
                "priority": "medium",
                "action_label": f"Reduce stock to {int(avg_demand * 0.8)} units",
                "business_reason": "Declining demand trend",
                "expected_impact": "Reduce excess inventory and carrying costs",
                "estimated_savings": round(avg_demand * 20, 2),
                "recommended_quantity": int(avg_demand * 0.8),
                "stockout_probability": 0.05
            },
            "reorder": {
                "title": f"🔄 REORDER - SKU {sku}",
                "description": f"Reorder {int(avg_demand * 1.2)} units to maintain optimal inventory.",
                "category": "reorder",
                "priority": "medium",
                "action_label": f"Reorder {int(avg_demand * 1.2)} units",
                "business_reason": "Maintain optimal inventory levels",
                "expected_impact": "Ensure continuous supply",
                "estimated_savings": round(avg_demand * 15, 2),
                "recommended_quantity": int(avg_demand * 1.2),
                "stockout_probability": 0.15
            },
            "procurement": {
                "title": f"📦 PROCUREMENT - SKU {sku}",
                "description": f"Increase procurement by {int(avg_demand * 0.4)} units to meet growing demand.",
                "category": "procurement",
                "priority": "high" if trend_strength == "strong" else "medium",
                "action_label": f"Procure {int(avg_demand * 1.4)} units",
                "business_reason": "Increasing demand trend",
                "expected_impact": "Meet growing demand",
                "estimated_savings": round(avg_demand * 25, 2),
                "recommended_quantity": int(avg_demand * 1.4),
                "stockout_probability": 0.25
            },
            "safety_stock": {
                "title": f"🛡️ SAFETY STOCK - SKU {sku}",
                "description": f"Increase safety stock to {int(safety_stock)} units due to demand variability.",
                "category": "inventory_optimization",
                "priority": "high",
                "action_label": f"Add {int(safety_stock)} units to safety stock",
                "business_reason": "High demand variability",
                "expected_impact": "Reduce stockout risk",
                "estimated_savings": round(avg_demand * 10, 2),
                "recommended_quantity": int(safety_stock),
                "stockout_probability": 0.10
            },
            "overstock": {
                "title": f"📦 OVERSTOCK - SKU {sku}",
                "description": f"Reduce overstock by {int(avg_demand * 0.3)} units due to decreasing demand.",
                "category": "overstock_management",
                "priority": "medium",
                "action_label": f"Reduce stock by {int(avg_demand * 0.3)} units",
                "business_reason": "Excess inventory due to demand drop",
                "expected_impact": "Reduce carrying costs",
                "estimated_savings": round(avg_demand * 12, 2),
                "recommended_quantity": int(avg_demand * 0.7),
                "stockout_probability": 0.02
            },
            "low_confidence_alert": {
                "title": f"⚠️ LOW CONFIDENCE - SKU {sku}",
                "description": f"Forecast confidence is low ({confidence_score:.0f}%). Manual review recommended.",
                "category": "risk_management",
                "priority": "medium",
                "action_label": "Review forecast manually",
                "business_reason": "Uncertain demand pattern",
                "expected_impact": "Improve forecast accuracy",
                "estimated_savings": round(avg_demand * 5, 2),
                "recommended_quantity": int(avg_demand),
                "stockout_probability": 0.30
            },
            "seasonal_stock": {
                "title": f"🌸 SEASONAL STOCK - SKU {sku}",
                "description": f"Prepare for {len(peak_days)} seasonal peaks. Stock up in advance.",
                "category": "inventory_optimization",
                "priority": "medium",
                "action_label": f"Prepare {int(max_demand * 1.5)} units for seasonal demand",
                "business_reason": "Seasonal demand pattern detected",
                "expected_impact": "Meet seasonal demand",
                "estimated_savings": round(avg_demand * 20, 2),
                "recommended_quantity": int(max_demand * 1.5),
                "stockout_probability": 0.20
            },
            "supplier_risk": {
                "title": f"🏭 SUPPLIER RISK - SKU {sku}",
                "description": f"Supplier risk detected. Consider alternative suppliers or negotiate terms.",
                "category": "supplier_management",
                "priority": "high",
                "action_label": "Review supplier contracts",
                "business_reason": "Supplier risk identified",
                "expected_impact": "Secure supply chain",
                "estimated_savings": round(avg_demand * 15, 2),
                "recommended_quantity": int(avg_demand * 1.2),
                "stockout_probability": 0.40
            },
            "inventory_optimization": {
                "title": f"📊 INVENTORY OPTIMIZATION - SKU {sku}",
                "description": f"Optimize inventory to {int(avg_demand * 1.1)} units for better efficiency.",
                "category": "inventory_optimization",
                "priority": "low",
                "action_label": f"Optimize to {int(avg_demand * 1.1)} units",
                "business_reason": "Optimize inventory levels",
                "expected_impact": "Improve inventory efficiency",
                "estimated_savings": round(avg_demand * 8, 2),
                "recommended_quantity": int(avg_demand * 1.1),
                "stockout_probability": 0.08
            },
            "bulk_purchase": {
                "title": f"📦 BULK PURCHASE - SKU {sku}",
                "description": f"Bulk purchase {int(avg_demand * 2)} units for better pricing.",
                "category": "procurement",
                "priority": "medium",
                "action_label": f"Bulk purchase {int(avg_demand * 2)} units",
                "business_reason": "Volume discount opportunity",
                "expected_impact": "Reduce unit cost",
                "estimated_savings": round(avg_demand * 35, 2),
                "recommended_quantity": int(avg_demand * 2),
                "stockout_probability": 0.05
            }
        }
        
        config = configs.get(rec_type, configs["inventory_optimization"])
        
        return {
            "sku": sku,
            "region": region,
            "warehouse": warehouse,
            "title": config["title"],
            "description": config["description"],
            "category": config["category"],
            "recommendation_type": rec_type,
            "priority": config["priority"],
            "business_reason": config["business_reason"],
            "action_label": config["action_label"],
            "expected_impact": config["expected_impact"],
            "estimated_savings": config["estimated_savings"],
            "recommended_quantity": config["recommended_quantity"],
            "stockout_probability": config["stockout_probability"],
            "ai_confidence": confidence_score,
            "forecast_accuracy": forecast_accuracy,
            "forecast_window": forecast_window,
            "forecast_value": avg_demand,
            "current_demand": avg_demand,
            "predicted_demand": avg_demand * 1.1,
            "supplier_name": None,
            "supplier_discount_available": False,
            "discount_days": None,
            "lead_time": "5-7 days",
            "inventory_days": 30,
            "holding_cost": round(avg_demand * 0.1, 2),
            "estimated_revenue": round(avg_demand * 100, 2),
            "estimated_cost": round(avg_demand * 70, 2),
            "estimated_loss": round(avg_demand * 20, 2),
            "forecast_summary": {
                "accuracy": forecast_accuracy,
                "window": forecast_window,
                "avg_demand": avg_demand
            },
            "related_forecast": {
                "trend": trend_direction,
                "peaks": len(peak_days)
            },
            "analysis": {
                "type": rec_type,
                "risk_score": risk_score,
                "confidence": confidence_score
            },
            "key_details": [
                {"label": "Average Demand", "value": f"{avg_demand:.0f} units"},
                {"label": "Forecast Accuracy", "value": f"{forecast_accuracy:.0f}%"},
                {"label": "Confidence", "value": f"{confidence_score:.0f}%"},
                {"label": "Risk Level", "value": "High" if risk_score > 60 else "Medium" if risk_score > 30 else "Low"},
                {"label": "Lead Time", "value": "5-7 days"},
                {"label": "Stockout Probability", "value": f"{config['stockout_probability']*100:.0f}%"}
            ]
        }
    
    # ============================================================
    # PROCESSING PIPELINE
    # ============================================================
    
    @staticmethod
    def _process_batch(
        recommendations: List[Dict[str, Any]],
        default_risk_score: float = 40
    ) -> List[Dict[str, Any]]:
        """Process a batch of recommendations: validate, deduplicate, score."""
        if not recommendations:
            return []
        
        # 1. Validate
        validated = []
        invalid = []
        for rec in recommendations:
            if RecommendationGeneratorService._validate_single(rec):
                validated.append(rec)
            else:
                invalid.append(rec)
        
        # 2. Remove duplicates within batch
        unique, removed = RecommendationGeneratorService._remove_duplicates(validated)
        
        # 3. Calculate scores
        scored = []
        for rec in unique:
            rec["recommendation_score"] = RecommendationGeneratorService._calculate_score(rec)
            if not rec.get("risk_score"):
                rec["risk_score"] = default_risk_score
            scored.append(rec)
        
        return scored
    
    @staticmethod
    def _validate_single(recommendation: Dict[str, Any]) -> bool:
        """Validate a single recommendation."""
        required_fields = [
            "sku", "title", "recommendation_type",
            "priority", "recommended_quantity"
        ]
        
        for field in required_fields:
            if not recommendation.get(field):
                return False
        
        if recommendation.get("recommended_quantity", 0) <= 0:
            return False
        
        confidence = recommendation.get("ai_confidence", 0)
        if confidence < 0 or confidence > 100:
            return False
        
        valid_priorities = ["critical", "high", "medium", "low"]
        if recommendation.get("priority") not in valid_priorities:
            return False
        
        return True
    
    @staticmethod
    def _remove_duplicates(
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
    def _calculate_score(recommendation: Dict[str, Any]) -> float:
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