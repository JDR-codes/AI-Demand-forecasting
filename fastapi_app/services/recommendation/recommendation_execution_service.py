#fastapi_app/services/recommendation/recommendation_execution_service.py
"""
Recommendation Execution Service - Full pipeline execution with step tracking.
"""
import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from fastapi_app.models.recommendation_job_model import (
    RecommendationJob,
    RecommendationJobStatus,
    RecommendationJobStep
)
from fastapi_app.models.recommendation_result_model import (
    RecommendationResult,
    RecommendationResultStatus
)
from fastapi_app.models.forecast_job_model import ForecastJob, ForecastResult
from fastapi_app.services.forecast.forecast_result_service import ForecastResultService
from fastapi_app.services.recommendation.recommendation_job_service import RecommendationJobService
from fastapi_app.services.recommendation.recommendation_analysis_service import RecommendationAnalysisService
from fastapi_app.services.recommendation.recommendation_generator_service import RecommendationGeneratorService
from fastapi_app.services.recommendation.recommendation_utils_service import RecommendationUtilsService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.services.background.task_manager import TaskManager

import logging
logger = logging.getLogger(__name__)


class RecommendationExecutionService:
    """Service for executing recommendation jobs."""
    
    @staticmethod
    def start_job_from_forecast(
        db: Session,
        forecast_job_id: str,
        forecast_summary: Optional[Dict[str, Any]] = None
    ) -> Optional[RecommendationJob]:
        """Start a recommendation job from a completed forecast."""
        # Create job
        job = RecommendationJobService.create_job(
            db=db,
            forecast_job_id=forecast_job_id,
            forecast_summary=forecast_summary
        )
        
        if not job:
            return None
        
        # Run in background
        TaskManager.run_recommendation_job(forecast_job_id)
        
        return job
    
    @staticmethod
    def run_job(db: Session, job_id: str) -> Optional[RecommendationJob]:
        """Execute the recommendation job in background."""
        job = RecommendationJobService.get_job(db, job_id)
        if not job:
            return None
        
        if job.status != RecommendationJobStatus.QUEUED:
            return job
        
        # Use asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                RecommendationExecutionService._execute_job(db, job_id)
            )
            return result
        finally:
            loop.close()
    
    @staticmethod
    async def _execute_job(db: Session, job_id: str) -> Optional[RecommendationJob]:
        """Execute the recommendation job in background."""
        job = RecommendationJobService.get_job(db, job_id)
        if not job:
            return None
        
        start_time = time.time()
        total_steps = 12
        forecast_results = None
        forecast_summary = None
        analysis = None
        recommendations = []
        validated_recommendations = []
        
        try:
            # Get forecast job
            forecast_job = db.query(ForecastJob).filter(
                ForecastJob.id == job.forecast_job_internal_id
            ).first()
            
            if not forecast_job:
                raise ValueError(f"Forecast job {job.forecast_job_id} not found")
            
            # Update status
            job.status = RecommendationJobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.started_by = job.created_by
            db.commit()
            
            # Send WebSocket: started
            await manager.send_recommendation_update({
                "type": "recommendation_started",
                "job_id": job.job_id,
                "forecast_job_id": job.forecast_job_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Execute steps
            steps = [
                (1, "loading_forecast", "Loading Forecast"),
                (2, "loading_summary", "Loading Forecast Summary"),
                (3, "reading_results", "Reading Forecast Results"),
                (4, "demand_analysis", "Demand Analysis"),
                (5, "inventory_analysis", "Inventory Analysis"),
                (6, "risk_analysis", "Risk Analysis"),
                (7, "generating_recommendations", "Generating Recommendations"),
                (8, "removing_duplicates", "Removing Duplicates"),
                (9, "validating", "Validating Recommendations"),
                (10, "saving_recommendations", "Saving Recommendations"),
                (11, "notifying", "Sending Notifications"),
                (12, "refreshing_dashboard", "Refreshing Dashboard"),
            ]
            
            for step_num, step_name_enum, step_name in steps:
                # Check for cancellation
                if job.status == RecommendationJobStatus.CANCELLED:
                    logger.info(f"Recommendation job {job_id} cancelled")
                    break
                
                # Check for pause
                while job.status == RecommendationJobStatus.PAUSED:
                    logger.info(f"Recommendation job {job_id} paused")
                    await asyncio.sleep(1)
                    db.refresh(job)
                
                # Update step
                RecommendationJobService.update_step(
                    db, job.id, step_num, "running", message=f"Starting {step_name}..."
                )
                RecommendationJobService.update_progress(
                    db, job.id, ((step_num - 1) / total_steps) * 100,
                    step_num, step_name, f"Starting {step_name}..."
                )
                db.commit()
                
                # Execute step
                step_start = time.time()
                
                if step_name_enum == "loading_forecast":
                    forecast_job = await RecommendationExecutionService._step_load_forecast(
                        db, job, forecast_job
                    )
                    
                elif step_name_enum == "loading_summary":
                    forecast_summary = await RecommendationExecutionService._step_load_summary(
                        db, job, forecast_job
                    )
                    
                elif step_name_enum == "reading_results":
                    forecast_results = await RecommendationExecutionService._step_read_results(
                        db, job, forecast_job
                    )
                    
                elif step_name_enum == "demand_analysis":
                    analysis = await RecommendationExecutionService._step_demand_analysis(
                        db, job, forecast_job, forecast_results, forecast_summary
                    )
                    
                elif step_name_enum == "inventory_analysis":
                    analysis = await RecommendationExecutionService._step_inventory_analysis(
                        db, job, analysis
                    )
                    
                elif step_name_enum == "risk_analysis":
                    analysis = await RecommendationExecutionService._step_risk_analysis(
                        db, job, analysis
                    )
                    
                elif step_name_enum == "generating_recommendations":
                    recommendations = await RecommendationExecutionService._step_generate_recommendations(
                        db, job, forecast_job, analysis, forecast_results
                    )
                    
                elif step_name_enum == "removing_duplicates":
                    recommendations, removed = await RecommendationExecutionService._step_remove_duplicates(
                        db, job, recommendations
                    )
                    job.duplicates_removed = removed
                    db.commit()
                    
                elif step_name_enum == "validating":
                    validated_recommendations = await RecommendationExecutionService._step_validate(
                        db, job, recommendations
                    )
                    
                elif step_name_enum == "saving_recommendations":
                    await RecommendationExecutionService._step_save_recommendations(
                        db, job, validated_recommendations or recommendations
                    )
                    
                elif step_name_enum == "notifying":
                    await RecommendationExecutionService._step_notify(
                        db, job, validated_recommendations or recommendations
                    )
                    
                elif step_name_enum == "refreshing_dashboard":
                    await RecommendationExecutionService._step_refresh_dashboard(
                        db, job
                    )
                
                # Mark step completed
                step_duration = time.time() - step_start
                RecommendationJobService.update_step(
                    db, job.id, step_num, "completed", step_duration,
                    f"Completed {step_name}"
                )
                
                # Update progress
                progress = (step_num / total_steps) * 100
                RecommendationJobService.update_progress(
                    db, job.id, progress, step_num, step_name,
                    f"Completed {step_name}"
                )
                
                # Calculate ETA
                elapsed = time.time() - start_time
                if step_num > 0:
                    avg_step_time = elapsed / step_num
                    remaining_steps = total_steps - step_num
                    job.remaining_seconds = avg_step_time * remaining_steps
                    job.estimated_completion = datetime.utcnow() + timedelta(seconds=job.remaining_seconds)
                    db.commit()
                
                # Send WebSocket progress
                await manager.send_recommendation_update({
                    "type": "recommendation_progress",
                    "job_id": job.job_id,
                    "progress": progress,
                    "step": step_name,
                    "step_number": step_num,
                    "total_steps": total_steps,
                    "remaining_time": job.remaining_seconds,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # If not cancelled, mark as completed
            if job.status != RecommendationJobStatus.CANCELLED:
                job.status = RecommendationJobStatus.COMPLETED
                job.progress_percentage = 100.0
                job.completed_at = datetime.utcnow()
                job.elapsed_time = time.time() - start_time
                job.total_processing_time = job.elapsed_time
                job.job_duration = job.elapsed_time
                job.total_recommendations = len(validated_recommendations or recommendations)
                job.saved_recommendations = job.total_recommendations
                job.current_step_message = f"Generated {job.total_recommendations} recommendations"
                
                # Calculate overall score
                recs_to_score = validated_recommendations or recommendations
                if recs_to_score:
                    scores = []
                    for r in recs_to_score:
                        score = r.get("recommendation_score", 0) or RecommendationUtilsService.calculate_score(r)
                        scores.append(score)
                    job.recommendation_score = sum(scores) / len(scores) if scores else 0
                
                db.commit()
                
                # Send completion notification
                await manager.send_recommendation_update({
                    "type": "recommendation_completed",
                    "job_id": job.job_id,
                    "forecast_job_id": job.forecast_job_id,
                    "count": job.total_recommendations,
                    "score": job.recommendation_score,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Send dashboard update
                await manager.send_dashboard_update({
                    "type": "recommendation_dashboard",
                    "action": "refresh",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Recommendation job {job_id} completed with {job.total_recommendations} recommendations")
                
        except Exception as e:
            logger.error(f"Recommendation job {job_id} failed: {str(e)}")
            job.status = RecommendationJobStatus.FAILED
            job.failed_step = job.current_step
            job.failed_step_name = job.current_step_name
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job.current_step_message = f"Failed at {job.current_step_name}: {str(e)}"
            db.commit()
            
            await manager.send_recommendation_update({
                "type": "recommendation_failed",
                "job_id": job.job_id,
                "error": str(e),
                "step": job.current_step_name,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        db.refresh(job)
        return job
    
    # ========== STEP METHODS ==========
    
    @staticmethod
    async def _step_load_forecast(db: Session, job: RecommendationJob, forecast_job: ForecastJob) -> ForecastJob:
        """Step 1: Load forecast job."""
        job.current_step_message = f"Loaded forecast job {forecast_job.job_id}"
        db.commit()
        return forecast_job
    
    @staticmethod
    async def _step_load_summary(db: Session, job: RecommendationJob, forecast_job: ForecastJob) -> Dict[str, Any]:
        """Step 2: Load forecast summary."""
        summary = ForecastResultService.get_summary(db, forecast_job.job_id)
        if "error" in summary:
            raise ValueError(summary["error"])
        
        job.forecast_summary = summary
        job.current_step_message = f"Loaded forecast summary with {summary.get('total_points', 0)} points"
        db.commit()
        return summary
    
    @staticmethod
    async def _step_read_results(
        db: Session,
        job: RecommendationJob,
        forecast_job: ForecastJob
    ) -> List[Dict[str, Any]]:
        """Step 3: Read forecast results."""
        results = db.query(ForecastResult).filter(
            ForecastResult.forecast_job_id == forecast_job.id,
            ForecastResult.is_forecast == True
        ).order_by(ForecastResult.forecast_date).all()
        
        if not results:
            raise ValueError("No forecast results found")
        
        result_data = [{
            "date": r.forecast_date,
            "prediction": r.prediction,
            "confidence_score": r.confidence_score,
            "is_peak": r.is_peak,
            "sku": r.sku,
            "region": r.region,
            "warehouse": r.warehouse
        } for r in results]
        
        job.current_step_message = f"Read {len(results)} forecast results"
        db.commit()
        return result_data
    
    @staticmethod
    async def _step_demand_analysis(
        db: Session,
        job: RecommendationJob,
        forecast_job: ForecastJob,
        forecast_results: List[Dict[str, Any]],
        forecast_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 4: Demand analysis."""
        predictions = [r["prediction"] for r in forecast_results]
        dates = [r["date"] for r in forecast_results]
        
        analysis = RecommendationAnalysisService.analyze_demand(
            predictions=predictions,
            dates=dates,
            sku=forecast_job.sku,
            region=forecast_job.region,
            warehouse=forecast_job.warehouse,
            forecast_summary=forecast_summary
        )
        
        job.current_step_message = f"Demand analysis complete: {analysis.get('trend', {}).get('direction', 'unknown')} trend"
        db.commit()
        return analysis
    
    @staticmethod
    async def _step_inventory_analysis(
        db: Session,
        job: RecommendationJob,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 5: Inventory analysis."""
        inventory_analysis = RecommendationAnalysisService.analyze_inventory(analysis)
        analysis["inventory"] = inventory_analysis
        
        job.current_step_message = f"Inventory analysis complete: {inventory_analysis.get('overall_status', 'unknown')}"
        db.commit()
        return analysis
    
    @staticmethod
    async def _step_risk_analysis(
        db: Session,
        job: RecommendationJob,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 6: Risk analysis."""
        risk_analysis = RecommendationAnalysisService.analyze_risk(analysis)
        analysis["risk"] = risk_analysis
        
        job.current_step_message = f"Risk analysis complete: {risk_analysis.get('overall_risk', 'unknown')} risk"
        db.commit()
        return analysis
    
    @staticmethod
    async def _step_generate_recommendations(
        db: Session,
        job: RecommendationJob,
        forecast_job: ForecastJob,
        analysis: Dict[str, Any],
        forecast_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Step 7: Generate recommendations."""
        recommendations = RecommendationGeneratorService.generate_recommendations(
            analysis=analysis,
            forecast_results=forecast_results,
            sku=forecast_job.sku,
            region=forecast_job.region,
            warehouse=forecast_job.warehouse,
            user_id=job.created_by,
            forecast_summary=job.forecast_summary
        )
        
        job.total_recommendations = len(recommendations)
        job.current_step_message = f"Generated {len(recommendations)} recommendations"
        db.commit()
        return recommendations
    
    @staticmethod
    async def _step_remove_duplicates(
        db: Session,
        job: RecommendationJob,
        recommendations: List[Dict[str, Any]]
    ) -> tuple:
        """Step 8: Remove duplicates using UtilsService."""
        if not recommendations:
            return [], 0
        
        # Use RecommendationUtilsService for deduplication
        unique_recommendations, removed = RecommendationUtilsService.remove_duplicates(recommendations)
        
        job.current_step_message = f"Removed {removed} duplicates, kept {len(unique_recommendations)}"
        db.commit()
        return unique_recommendations, removed
    
    @staticmethod
    async def _step_validate(
        db: Session,
        job: RecommendationJob,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Step 9: Validate recommendations using UtilsService."""
        if not recommendations:
            return []
        
        validated, invalid = RecommendationUtilsService.validate_recommendations(recommendations)
        
        job.current_step_message = f"Validated {len(validated)} recommendations, {len(invalid)} invalid"
        db.commit()
        return validated
    
    @staticmethod
    async def _step_save_recommendations(
        db: Session,
        job: RecommendationJob,
        recommendations: List[Dict[str, Any]]
    ) -> None:
        """Step 10: Save recommendations."""
        if not recommendations:
            job.current_step_message = "No recommendations to save"
            db.commit()
            return
        
        saved_count = 0
        for rec_data in recommendations:
            # Calculate score if not present
            if not rec_data.get("recommendation_score"):
                rec_data["recommendation_score"] = RecommendationUtilsService.calculate_score(rec_data)
            
            # Create recommendation result
            rec = RecommendationResult(
                recommendation_job_id=job.id,
                forecast_job_id=job.forecast_job_id,
                sku=rec_data.get("sku", "default"),
                title=rec_data.get("title", "Recommendation"),
                description=rec_data.get("description", ""),
                business_reason=rec_data.get("business_reason", ""),
                category=rec_data.get("category"),
                recommendation_type=rec_data.get("recommendation_type"),
                priority=rec_data.get("priority"),
                status=RecommendationResultStatus.PENDING,
                recommended_quantity=rec_data.get("recommended_quantity", 0),
                current_stock=rec_data.get("current_stock"),
                lead_time=rec_data.get("lead_time", "5-7 days"),
                inventory_days=rec_data.get("inventory_days"),
                holding_cost=rec_data.get("holding_cost"),
                stockout_probability=rec_data.get("stockout_probability"),
                estimated_savings=rec_data.get("estimated_savings"),
                estimated_revenue=rec_data.get("estimated_revenue"),
                estimated_cost=rec_data.get("estimated_cost"),
                estimated_loss=rec_data.get("estimated_loss"),
                expected_impact=rec_data.get("expected_impact"),
                ai_confidence=rec_data.get("ai_confidence", 80.0),
                recommendation_score=rec_data.get("recommendation_score", 0),
                risk_score=rec_data.get("risk_score", 0),
                forecast_summary=rec_data.get("forecast_summary"),
                forecast_accuracy=rec_data.get("forecast_accuracy"),
                forecast_window=rec_data.get("forecast_window"),
                related_forecast=rec_data.get("related_forecast"),
                action_label=rec_data.get("action_label"),
                warehouse=rec_data.get("warehouse"),
                region=rec_data.get("region"),
                forecast_value=rec_data.get("forecast_value"),
                current_demand=rec_data.get("current_demand"),
                predicted_demand=rec_data.get("predicted_demand"),
                supplier_name=rec_data.get("supplier_name"),
                supplier_discount_available=rec_data.get("supplier_discount_available", False),
                discount_days=rec_data.get("discount_days"),
                analysis=rec_data.get("analysis"),
                key_details=rec_data.get("key_details", [])
            )
            db.add(rec)
            saved_count += 1
        
        db.commit()
        
        job.saved_recommendations = saved_count
        job.current_step_message = f"Saved {saved_count} recommendations"
        db.commit()
    
    @staticmethod
    async def _step_notify(
        db: Session,
        job: RecommendationJob,
        recommendations: List[Dict[str, Any]]
    ) -> None:
        """Step 11: Send notifications using UtilsService."""
        if not recommendations or not job.created_by:
            job.current_step_message = "No notifications sent"
            db.commit()
            return
        
        # Send notifications for critical and high priority
        RecommendationUtilsService.send_bulk_notification(
            db=db,
            user_id=job.created_by,
            recommendations=recommendations,
            action="generated"
        )
        
        job.current_step_message = f"Sent notifications for {len(recommendations)} recommendations"
        db.commit()
    
    @staticmethod
    async def _step_refresh_dashboard(db: Session, job: RecommendationJob) -> None:
        """Step 12: Refresh dashboard."""
        await manager.send_dashboard_update({
            "type": "recommendation_saved",
            "job_id": job.job_id,
            "count": job.saved_recommendations,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        job.current_step_message = "Dashboard refreshed"
        db.commit()
    
    # ========== JOB CONTROL METHODS ==========
    
    @staticmethod
    def pause_job(db: Session, job_id: str) -> bool:
        return RecommendationJobService.pause_job(db, job_id)
    
    @staticmethod
    def resume_job(db: Session, job_id: str) -> bool:
        return RecommendationJobService.resume_job(db, job_id)
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> bool:
        return RecommendationJobService.cancel_job(db, job_id)
    
    @staticmethod
    def retry_job(db: Session, job_id: str) -> Optional[RecommendationJob]:
        return RecommendationJobService.retry_job(db, job_id)
    
    @staticmethod
    def get_live_status(db: Session, job_id: str) -> Dict[str, Any]:
        return RecommendationJobService.get_live_status(db, job_id)