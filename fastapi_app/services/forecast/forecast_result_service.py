# fastapi_app/services/forecast/forecast_result_service.py
"""
Forecast Result Service - Loads and formats forecast results for UI.
Provides comprehensive summary data for recommendations.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import numpy as np

from fastapi_app.models.forecast_job_model import ForecastResult, ForecastJob


class ForecastResultService:
    """Service for forecast results - provides summary data for UI and Recommendations."""
    
    @staticmethod
    def get_summary(db: Session, job_id: str) -> Dict[str, Any]:
        """
        Get comprehensive forecast summary.
        Returns all data needed for recommendations.
        """
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return {"error": "Job not found"}
        
        results = db.query(ForecastResult).filter(
            ForecastResult.forecast_job_id == job.id,
            ForecastResult.is_forecast == True
        ).order_by(ForecastResult.forecast_date).all()
        
        if not results:
            return {"error": "No forecast results found"}
        
        # Extract data
        predictions = [r.prediction for r in results]
        dates = [r.forecast_date for r in results]
        confidence_scores = [r.confidence_score for r in results if r.confidence_score]
        
        # Basic statistics
        total_demand = sum(predictions)
        avg_demand = total_demand / len(predictions) if predictions else 0
        std_dev = np.std(predictions) if predictions else 0
        max_demand = max(predictions) if predictions else 0
        min_demand = min(predictions) if predictions else 0
        
        # Peak analysis
        peak_idx = np.argmax(predictions) if predictions else 0
        peak_day = peak_idx + 1
        peak_value = predictions[peak_idx] if predictions else 0
        
        # Get peaks (top 5)
        sorted_indices = np.argsort(predictions)[::-1] if predictions else []
        peaks = []
        for i in sorted_indices[:5]:
            if i < len(predictions):
                peaks.append({
                    "day": i + 1,
                    "date": dates[i].isoformat() if i < len(dates) else None,
                    "value": round(predictions[i], 2),
                    "confidence": confidence_scores[i] if i < len(confidence_scores) else 0.85
                })
        
        # Trend analysis
        trend = ForecastResultService._analyze_trend(predictions)
        
        # Inventory risk
        coefficient_var = std_dev / avg_demand if avg_demand > 0 else 0
        if coefficient_var < 0.1:
            inventory_risk = "Low"
            safety_stock_pct = 0.1
        elif coefficient_var < 0.25:
            inventory_risk = "Medium"
            safety_stock_pct = 0.2
        else:
            inventory_risk = "High"
            safety_stock_pct = 0.35
        
        # Financial metrics
        unit_price = job.configuration.get("unit_price", 30.0) if job.configuration else 30.0
        holding_cost_pct = job.configuration.get("holding_cost_pct", 0.25) if job.configuration else 0.25
        
        expected_revenue = total_demand * unit_price
        safety_stock = avg_demand * safety_stock_pct
        holding_cost = (total_demand * unit_price * holding_cost_pct) / 365 * len(predictions)
        
        # Accuracy
        accuracy = job.metrics.get("accuracy", 0.85) if job.metrics else 0.85
        
        # Confidence
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.85
        
        # Forecast window
        forecast_start = dates[0] if dates else None
        forecast_end = dates[-1] if dates else None
        forecast_window = (forecast_end - forecast_start).days + 1 if forecast_start and forecast_end else 0
        
        # Supplier and lead time from config
        supplier = job.configuration.get("supplier") if job.configuration else None
        lead_time = job.configuration.get("lead_time", "5-7 days") if job.configuration else "5-7 days"
        
        return {
            # Basic metrics
            "forecasted_demand": round(total_demand, 2),
            "avg_daily_demand": round(avg_demand, 2),
            "max_demand": round(max_demand, 2),
            "min_demand": round(min_demand, 2),
            "std_dev": round(std_dev, 2),
            "coefficient_variation": round(coefficient_var, 3),
            
            # Peak metrics
            "peak_day": peak_day,
            "peak_value": round(peak_value, 2),
            "peaks": peaks,
            
            # Trend
            "trend": trend,
            "trend_direction": trend.get("direction", "stable"),
            "trend_strength": trend.get("strength", "weak"),
            
            # Financial
            "unit_price": unit_price,
            "expected_revenue": round(expected_revenue, 2),
            "holding_cost_pct": holding_cost_pct,
            "holding_cost": round(holding_cost, 2),
            "safety_stock": round(safety_stock, 2),
            
            # Risk
            "inventory_risk": inventory_risk,
            "risk_level": "Low" if inventory_risk == "Low" else "High" if inventory_risk == "High" else "Medium",
            
            # Accuracy and confidence
            "accuracy": round(accuracy * 100, 1),
            "confidence_level": round(avg_confidence, 2),
            
            # Forecast window
            "forecast_window": forecast_window,
            "forecast_start": forecast_start.isoformat() if forecast_start else None,
            "forecast_end": forecast_end.isoformat() if forecast_end else None,
            
            # Location
            "sku": job.sku,
            "region": job.region,
            "warehouse": job.warehouse,
            
            # Supplier
            "supplier": supplier,
            "lead_time": lead_time,
            
            # Model
            "model_type": job.metrics.get("model_type", "unknown") if job.metrics else "unknown",
            "model_accuracy": job.metrics.get("accuracy") if job.metrics else None,
            
            # Raw data
            "demand_values": [round(v, 2) for v in predictions],
            "dates": [d.isoformat() for d in dates] if dates else [],
            "confidence_scores": [round(c, 2) for c in confidence_scores],
            
            # Total points
            "total_points": len(results),
            
            # Metadata
            "job_id": job.job_id,
            "job_status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
    
    @staticmethod
    def _analyze_trend(predictions: List[float]) -> Dict[str, Any]:
        """Analyze trend in forecast values."""
        if len(predictions) < 3:
            return {"direction": "stable", "strength": "weak", "slope": 0, "r2": 0}
        
        x = np.arange(len(predictions))
        y = np.array(predictions)
        
        # Linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Determine direction
        mean_y = np.mean(y)
        if slope > 0.05 * mean_y:
            direction = "increasing"
        elif slope < -0.05 * mean_y:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # Calculate R²
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
            "r2": round(r2, 3),
            "description": f"{direction.capitalize()} trend with {strength} confidence"
        }
    
    @staticmethod
    def get_peak_days(db: Session, job_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get peak demand days."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return []
        
        results = db.query(ForecastResult).filter(
            ForecastResult.forecast_job_id == job.id,
            ForecastResult.is_forecast == True
        ).order_by(ForecastResult.prediction.desc()).limit(top_n).all()
        
        return [
            {
                "day": r.forecast_date.strftime("%Y-%m-%d"),
                "demand": r.prediction,
                "confidence": r.confidence_score or 0.85
            }
            for r in results
        ]
    
    @staticmethod
    def get_forecast_results(db: Session, job_id: str) -> List[Dict[str, Any]]:
        """Get all forecast results for a job."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return []
        
        results = db.query(ForecastResult).filter(
            ForecastResult.forecast_job_id == job.id
        ).order_by(ForecastResult.forecast_date).all()
        
        return [
            {
                "date": r.forecast_date.isoformat(),
                "prediction": r.prediction,
                "actual_value": r.actual_value,
                "confidence_score": r.confidence_score,
                "is_forecast": r.is_forecast,
                "is_peak": r.is_peak,
                "sku": r.sku,
                "region": r.region,
                "warehouse": r.warehouse,
                "model_used": r.model_used
            }
            for r in results
        ]