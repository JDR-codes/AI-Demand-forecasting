# fastapi_app/services/recommendation/recommendation_analysis_service.py
"""
Recommendation Analysis Service - Multi-dimensional analysis for recommendations.
Only performs analysis, no database operations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np


class RecommendationAnalysisService:
    """Service for comprehensive analysis of forecast data."""
    
    @staticmethod
    def analyze_demand(
        predictions: List[float],
        dates: List[datetime],
        sku: Optional[str] = None,
        region: Optional[str] = None,
        warehouse: Optional[str] = None,
        forecast_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze demand patterns from forecast predictions."""
        if not predictions or len(predictions) < 3:
            return {
                "error": "Insufficient data for analysis",
                "demand_score": 0,
                "trend_score": 0,
                "confidence_score": 0,
                "sku": sku,
                "region": region,
                "warehouse": warehouse
            }
        
        # Basic statistics
        avg_demand = sum(predictions) / len(predictions)
        std_dev = np.std(predictions)
        max_demand = max(predictions)
        min_demand = min(predictions)
        
        # Coefficient of variation
        cv = std_dev / avg_demand if avg_demand > 0 else 0
        
        # Trend analysis
        trend = RecommendationAnalysisService._analyze_trend(predictions)
        trend_score = RecommendationAnalysisService._calculate_trend_score(trend)
        
        # Peak analysis
        peak_days = []
        threshold = avg_demand + std_dev
        for i, value in enumerate(predictions):
            if value > threshold:
                peak_days.append({
                    "day": i + 1,
                    "value": round(value, 2),
                    "date": dates[i].isoformat() if i < len(dates) else None
                })
        
        peak_score = min(100, len(peak_days) * 15) if peak_days else 0
        
        # Confidence score
        confidence_score = max(0, min(100, (1 - cv) * 100))
        
        # Demand score
        demand_score = min(100, (avg_demand / (max_demand + 1)) * 100) if max_demand > 0 else 0
        
        # Overall trend
        trend_summary = {
            "direction": trend.get("direction", "stable"),
            "strength": trend.get("strength", "weak"),
            "slope": trend.get("slope", 0)
        }
        
        return {
            "demand_score": round(demand_score, 1),
            "trend_score": round(trend_score, 1),
            "confidence_score": round(confidence_score, 1),
            "peak_score": round(peak_score, 1),
            
            "average_demand": round(avg_demand, 2),
            "max_demand": round(max_demand, 2),
            "min_demand": round(min_demand, 2),
            "std_dev": round(std_dev, 2),
            "coefficient_variation": round(cv, 3),
            "total_demand": round(sum(predictions), 2),
            "point_count": len(predictions),
            
            "peak_days": peak_days[:5],
            "trend": trend_summary,
            
            "sku": sku,
            "region": region,
            "warehouse": warehouse
        }
    
    @staticmethod
    def analyze_inventory(analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze inventory implications."""
        avg_demand = analysis.get("average_demand", 0)
        cv = analysis.get("coefficient_variation", 0)
        trend = analysis.get("trend", {})
        peak_days = analysis.get("peak_days", [])
        
        # Inventory status
        if cv > 0.3:
            volatility = "high"
            safety_stock_pct = 0.35
        elif cv > 0.15:
            volatility = "medium"
            safety_stock_pct = 0.2
        else:
            volatility = "low"
            safety_stock_pct = 0.1
        
        # Trend impact
        trend_dir = trend.get("direction", "stable")
        if trend_dir == "increasing":
            trend_impact = "positive"
            demand_growth = "increasing"
        elif trend_dir == "decreasing":
            trend_impact = "negative"
            demand_growth = "decreasing"
        else:
            trend_impact = "neutral"
            demand_growth = "stable"
        
        # Peak impact
        peak_count = len(peak_days)
        if peak_count > analysis.get("point_count", 0) * 0.3:
            peak_impact = "high"
        elif peak_count > 0:
            peak_impact = "medium"
        else:
            peak_impact = "low"
        
        # Overall inventory status
        if volatility == "high" or peak_impact == "high":
            overall_status = "high_risk"
            recommended_approach = "Increase safety stock and monitor daily"
        elif volatility == "medium" or peak_impact == "medium":
            overall_status = "moderate_risk"
            recommended_approach = "Review safety stock levels weekly"
        else:
            overall_status = "stable"
            recommended_approach = "Maintain current levels"
        
        return {
            "overall_status": overall_status,
            "volatility": volatility,
            "trend_impact": trend_impact,
            "peak_impact": peak_impact,
            "demand_growth": demand_growth,
            "safety_stock_pct": safety_stock_pct,
            "safety_stock_units": round(avg_demand * safety_stock_pct, 2),
            "recommended_approach": recommended_approach,
            "inventory_score": round(100 - (cv * 100), 1)
        }
    
    @staticmethod
    def analyze_risk(analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze business risk."""
        cv = analysis.get("coefficient_variation", 0)
        trend = analysis.get("trend", {})
        confidence_score = analysis.get("confidence_score", 0)
        peak_days = analysis.get("peak_days", [])
        
        # Business risk
        if cv > 0.3:
            business_risk = "high"
            risk_score = 80
        elif cv > 0.15:
            business_risk = "medium"
            risk_score = 50
        else:
            business_risk = "low"
            risk_score = 20
        
        # Trend risk
        trend_dir = trend.get("direction", "stable")
        if trend_dir == "decreasing" and trend.get("strength") == "strong":
            trend_risk = "high"
            risk_score += 20
        elif trend_dir == "decreasing":
            trend_risk = "medium"
            risk_score += 10
        else:
            trend_risk = "low"
        
        # Financial risk
        peak_count = len(peak_days)
        if peak_count > 0:
            financial_risk = "medium"
            risk_score += 10
        else:
            financial_risk = "low"
        
        # Confidence risk
        if confidence_score < 50:
            confidence_risk = "high"
            risk_score += 20
        elif confidence_score < 70:
            confidence_risk = "medium"
            risk_score += 10
        else:
            confidence_risk = "low"
        
        # Normalize risk score
        risk_score = min(100, risk_score)
        
        return {
            "overall_risk": business_risk if risk_score > 60 else "medium" if risk_score > 30 else "low",
            "business_risk": business_risk,
            "financial_risk": financial_risk,
            "trend_risk": trend_risk,
            "confidence_risk": confidence_risk,
            "risk_score": risk_score,
            "details": {
                "coefficient_variation": cv,
                "trend_direction": trend_dir,
                "peak_count": len(peak_days),
                "confidence": confidence_score
            },
            "risk_factors": RecommendationAnalysisService._get_risk_factors(risk_score)
        }
    
    @staticmethod
    def _analyze_trend(predictions: List[float]) -> Dict[str, Any]:
        """Analyze trend in forecast values."""
        if len(predictions) < 3:
            return {"direction": "stable", "strength": "weak", "slope": 0, "r2": 0}
        
        x = np.arange(len(predictions))
        y = np.array(predictions)
        
        slope, intercept = np.polyfit(x, y, 1)
        mean_y = np.mean(y)
        
        if slope > 0.05 * mean_y:
            direction = "increasing"
        elif slope < -0.05 * mean_y:
            direction = "decreasing"
        else:
            direction = "stable"
        
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - mean_y) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        if r2 > 0.6:
            strength = "strong"
        elif r2 > 0.3:
            strength = "moderate"
        else:
            strength = "weak"
        
        return {
            "direction": direction,
            "slope": round(slope, 3),
            "strength": strength,
            "r2": round(r2, 3)
        }
    
    @staticmethod
    def _calculate_trend_score(trend: Dict[str, Any]) -> float:
        """Calculate trend score (0-100)."""
        direction = trend.get("direction", "stable")
        strength = trend.get("strength", "weak")
        
        if direction == "increasing":
            base = 70
        elif direction == "decreasing":
            base = 30
        else:
            base = 50
        
        if strength == "strong":
            return min(100, base + 20)
        elif strength == "moderate":
            return base
        else:
            return max(0, base - 20)
    
    @staticmethod
    def _get_risk_factors(risk_score: float) -> List[str]:
        """Get risk factors based on risk score."""
        if risk_score > 70:
            return [
                "High demand volatility",
                "Significant trend changes",
                "Low confidence in forecast",
                "Multiple peak periods"
            ]
        elif risk_score > 40:
            return [
                "Moderate demand variability",
                "Some trend uncertainty",
                "Medium confidence level"
            ]
        else:
            return [
                "Stable demand pattern",
                "Clear trend direction",
                "High confidence in forecast"
            ]