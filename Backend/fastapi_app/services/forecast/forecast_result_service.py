# fastapi_app/services/forecast/forecast_result_service.py
"""
Forecast Result Service - Loads and formats forecast results for UI.
Results are handled by ForecastChartService for chart data.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import numpy as np

from fastapi_app.models.forecast_job_model import ForecastResult, ForecastJob, ForecastJobStatus


class ForecastResultService:
    """Service for forecast results - summary only. Chart data moved to ForecastChartService."""
    
    @staticmethod    
    def get_summary(db: Session, job_id: str) -> Dict[str, Any]:
        """Get summary statistics for a forecast job."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return {"error": "Job not found"}
        
        if job.status != ForecastJobStatus.COMPLETED:
            status_str = job.status.value if hasattr(job.status, "value") else str(job.status)
            return {"error": f"Job has not completed successfully. Current status: {status_str}"}
        
        results = db.query(ForecastResult).filter(
            ForecastResult.forecast_job_id == job.id,
            ForecastResult.is_forecast == True  # Only forecast points
        ).all()
        
        if not results:
            return {"error": "No forecast results found"}
        
        # Calculate metrics
        predictions = [r.prediction for r in results]
        total_demand = sum(predictions)
        avg_demand = total_demand / len(predictions) if predictions else 0
        
        # Find peak
        peak_idx = np.argmax(predictions) if predictions else 0
        peak_day = peak_idx + 1
        peak_value = predictions[peak_idx] if predictions else 0
        
        # Get unit price from configuration
        unit_price = job.configuration.get("unit_price", 30.0) if job.configuration else 30.0
        expected_revenue = total_demand * unit_price
        
        # Inventory risk (based on variability)
        std_dev = np.std(predictions) if predictions else 0
        coefficient_var = std_dev / avg_demand if avg_demand > 0 else 0
        if coefficient_var < 0.1:
            inventory_risk = "Low"
        elif coefficient_var < 0.25:
            inventory_risk = "Medium"
        else:
            inventory_risk = "High"
        
        # Accuracy from job metrics
        accuracy = job.metrics.get("accuracy", 0.85) if job.metrics else 0.85
        
        # Calculate confidence level from results
        confidence_scores = [r.confidence_score for r in results if r.confidence_score]
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.95
        
        return {
            "forecasted_demand": round(total_demand, 2),
            "avg_daily_demand": round(avg_demand, 2),
            "peak_day": peak_day,
            "peak_value": round(peak_value, 2),
            "expected_revenue": round(expected_revenue, 2),
            "inventory_risk": inventory_risk,
            "accuracy": round(accuracy * 100, 1),
            "total_points": len(results),
            "confidence_level": round(avg_confidence, 2),
            "unit_price_used": unit_price
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