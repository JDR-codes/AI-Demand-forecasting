# fastapi_app/services/forecast/forecast_chart_service.py
"""
Forecast Chart Service - Generates chart data for forecasts.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import numpy as np

from fastapi_app.models.forecast_job_model import ForecastJob, ForecastResult, ForecastJobStatus
from fastapi_app.services.forecast.forecast_result_service import ForecastResultService


class ForecastChartService:
    """Service for generating chart data from forecasts."""
    
    @staticmethod
    def get_chart_data(db: Session, job_id: str) -> Dict[str, Any]:
        """Get chart data with proper historical/forecast separation using is_forecast flag."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return {"error": "Job not found"}
        
        if job.status != ForecastJobStatus.COMPLETED:
            status_str = job.status.value if hasattr(job.status, "value") else str(job.status)
            return {"error": f"Job has not completed successfully. Current status: {status_str}"}
        
        results = db.query(ForecastResult).filter(
            ForecastResult.forecast_job_id == job.id
        ).order_by(ForecastResult.forecast_date).all()
        
        if not results:
            return {"error": "No results found"}
        
        # ✅ Separate historical and forecast using is_forecast flag
        historical = []
        forecast = []
        upper = []
        lower = []
        labels = []
        
        for r in results:
            labels.append(r.forecast_date.strftime("%Y-%m-%d"))
            if r.is_forecast:
                forecast.append(r.prediction)
                upper.append(r.confidence_upper or r.prediction * 1.1)
                lower.append(r.confidence_lower or r.prediction * 0.9)
            else:
                historical.append(r.prediction)
        
        # Find peaks in forecast
        peaks = []
        if forecast:
            forecast_array = np.array(forecast)
            threshold = np.mean(forecast_array) + np.std(forecast_array)
            for i, value in enumerate(forecast):
                if value > threshold:
                    peaks.append({
                        "index": len(historical) + i,
                        "value": float(value),
                        "date": labels[len(historical) + i] if len(labels) > len(historical) + i else None
                    })
        
        return {
            "historical": historical,
            "forecast": forecast,
            "upper": upper,
            "lower": lower,
            "labels": labels,
            "split_index": len(historical),
            "total_points": len(results),
            "peak_days": peaks[:5],
            "forecast_start": labels[len(historical)] if len(labels) > len(historical) else None
        }
    
    @staticmethod
    def get_summary(db: Session, job_id: str) -> Dict[str, Any]:
        """Get summary statistics."""
        return ForecastResultService.get_summary(db, job_id)
    
    @staticmethod
    def get_peaks(db: Session, job_id: str, top_n: int = 5) -> Dict[str, Any]:
        """Get peak days with details."""
        job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        if not job:
            return {"error": "Job not found"}
        
        if job.status != ForecastJobStatus.COMPLETED:
            status_str = job.status.value if hasattr(job.status, "value") else str(job.status)
            return {"error": f"Job has not completed successfully. Current status: {status_str}"}
        
        peaks = ForecastResultService.get_peak_days(db, job_id, top_n)
        
        return {
            "peaks": peaks,
            "total_peaks": len(peaks),
            "job_id": job_id
        }