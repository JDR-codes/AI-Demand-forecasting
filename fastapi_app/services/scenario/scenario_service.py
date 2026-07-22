# fastapi_app/services/scenario/scenario_service.py
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
import traceback
import logging

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import desc, func
from fastapi import BackgroundTasks

from fastapi_app.models.scenario_model import Scenario, ScenarioStatus, ScenarioRun, ScenarioResult
from fastapi_app.schemas.scenario_schema import ScenarioCreate, ScenarioUpdate, ScenarioFilter
from fastapi_app.services.scenario.simulation_engine import SimulationEngine
from fastapi_app.services.forecast.forecast_service import prepare_series
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class ScenarioService:
    
    # ============= CRUD =============
    
    @staticmethod
    def get_all_scenarios(
        db: Session,
        filter_params: Optional[ScenarioFilter] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get scenarios with all filters and pagination."""
        query = db.query(Scenario)
        
        if filter_params:
            if filter_params.search:
                search = f"%{filter_params.search}%"
                query = query.filter(
                    or_(
                        Scenario.name.ilike(search),
                        Scenario.description.ilike(search),
                        Scenario.sku.ilike(search)
                    )
                )
            if filter_params.status:
                query = query.filter(Scenario.status == filter_params.status)
            if filter_params.region:
                query = query.filter(Scenario.region == filter_params.region)
            if filter_params.warehouse:
                query = query.filter(Scenario.warehouse == filter_params.warehouse)
            if filter_params.category:
                query = query.filter(Scenario.category == filter_params.category)
            if filter_params.sku:
                query = query.filter(Scenario.sku == filter_params.sku)
            if filter_params.forecast_model:
                query = query.filter(Scenario.forecast_model == filter_params.forecast_model)
            if filter_params.created_by:
                query = query.filter(Scenario.created_by == filter_params.created_by)
            if filter_params.last_run_status:
                query = query.filter(Scenario.last_run_status == filter_params.last_run_status)
            if filter_params.start_date:
                query = query.filter(Scenario.created_at >= filter_params.start_date)
            if filter_params.end_date:
                query = query.filter(Scenario.created_at <= filter_params.end_date)
            
            # Sort
            sort = filter_params.sort or "-created_at"
            if sort.startswith("-"):
                query = query.order_by(desc(getattr(Scenario, sort[1:])))
            else:
                query = query.order_by(getattr(Scenario, sort))
        
        total = query.count()
        offset = (page - 1) * limit
        items = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1,
            "items": items
        }
    
    @staticmethod
    def get_scenario_by_id(db: Session, scenario_id: int) -> Optional[Scenario]:
        return db.query(Scenario).filter(Scenario.id == scenario_id).first()
    
    @staticmethod
    def create_scenario(db: Session, scenario_create: ScenarioCreate, user_id: int = None) -> Scenario:
        # Validate duplicate name
        existing = db.query(Scenario).filter(Scenario.name == scenario_create.name).first()
        if existing:
            raise ValueError(f"Scenario with name '{scenario_create.name}' already exists")
        
        scenario = Scenario(
            **scenario_create.model_dump(),
            created_by=user_id,
            status=ScenarioStatus.CREATED
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario
    
    @staticmethod
    def duplicate_scenario(db: Session, scenario_id: int, name: Optional[str] = None, user_id: int = None) -> Optional[Scenario]:
        """Duplicate an existing scenario."""
        original = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not original:
            return None
        
        new_name = name or f"{original.name} (Copy)"
        
        # Check for duplicate name
        existing = db.query(Scenario).filter(Scenario.name == new_name).first()
        if existing:
            new_name = f"{new_name} {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        scenario = Scenario(
            name=new_name,
            description=original.description,
            time_horizon=original.time_horizon,
            region=original.region,
            warehouse=original.warehouse,
            category=original.category,
            sku=original.sku,
            demand_surge=original.demand_surge,
            discount=original.discount,
            price_change=original.price_change,
            supply_delay=original.supply_delay,
            seasonal_impact=original.seasonal_impact,
            forecast_model=original.forecast_model,
            parameters=original.parameters,
            created_by=user_id,
            status=ScenarioStatus.CREATED
        )
        
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario
    
    @staticmethod
    def update_scenario(db: Session, scenario_id: int, scenario_update: ScenarioUpdate) -> Optional[Scenario]:
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return None
        
        update_data = scenario_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(scenario, key, value)
        
        scenario.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(scenario)
        return scenario
    
    @staticmethod
    def delete_scenario(db: Session, scenario_id: int) -> bool:
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return False
        
        db.delete(scenario)
        db.commit()
        return True
    
    @staticmethod
    def bulk_delete_scenarios(db: Session, scenario_ids: List[int]) -> Dict[str, int]:
        """Bulk delete scenarios."""
        deleted = 0
        failed = 0
        
        for sid in scenario_ids:
            if ScenarioService.delete_scenario(db, sid):
                deleted += 1
            else:
                failed += 1
        
        return {"deleted": deleted, "failed": failed}
    
    # ============= Run Simulation (Production Async) =============
    
    @staticmethod
    def run_scenario_async(
        db: Session,
        scenario_id: int,
        background_tasks: BackgroundTasks,
        user_id: int = None
    ) -> Optional[ScenarioRun]:
        """
        Start a scenario simulation asynchronously.
        Returns immediately with run_id.
        """
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return None
        
        # Validate scenario before running
        if scenario.status == ScenarioStatus.RUNNING:
            raise ValueError("Scenario is already running")
        
        # Create run record
        run_id = str(uuid.uuid4())
        run = ScenarioRun(
            scenario_id=scenario.id,
            run_id=run_id,
            status="queued",
            progress=0.0,
            user_id=user_id,
            logs=[],
            total_steps=len(SimulationEngine.STEPS)
        )
        db.add(run)
        
        # Update scenario
        scenario.status = ScenarioStatus.RUNNING
        scenario.progress = 0.0
        db.commit()
        db.refresh(run)
        
        # Send queued notification
        if user_id:
            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                title=f"⏳ Simulation Queued: {scenario.name}",
                message=f"Simulation for '{scenario.name}' is queued and will start shortly.",
                notification_type="scenario",
                priority="info"
            )
        
        # Start background task with isolated session
        background_tasks.add_task(
            ScenarioService._execute_simulation_background,
            scenario_id,
            run_id,
            user_id
        )
        
        # Send WebSocket update
        import threading
        import asyncio
        def send_ws_update():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    manager.send_dashboard_update({
                        "type": "scenario_queued",
                        "scenario_id": scenario.id,
                        "run_id": run.run_id,
                        "name": scenario.name,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )
                loop.close()
            except Exception as e:
                logger.error(f"Failed to send WebSocket update: {str(e)}")
        
        threading.Thread(target=send_ws_update, daemon=True).start()
        
        return run
    
    @staticmethod
    def _execute_simulation_background(
        scenario_id: int,
        run_id: str,
        user_id: int = None
    ):
        """
        Background task to execute simulation.
        Creates its own isolated database session.
        """
        # ✅ Create isolated session
        db = SessionLocal()
        
        try:
            # Get objects
            scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            run = db.query(ScenarioRun).filter(ScenarioRun.run_id == run_id).first()
            
            if not scenario or not run:
                logger.error(f"Scenario {scenario_id} or run {run_id} not found")
                return
            
            # Update run status
            run.status = "running"
            run.started_at = datetime.utcnow()
            db.commit()
            
            # Send started notification
            if user_id:
                NotificationService.create_notification(
                    db=db,
                    user_id=user_id,
                    title=f"🔬 Simulation Started: {scenario.name}",
                    message=f"Simulation for '{scenario.name}' is now running.",
                    notification_type="scenario",
                    priority="info"
                )
            
            # Send WebSocket started update
            import threading
            import asyncio
            def send_start_update():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        manager.send_dashboard_update({
                            "type": "scenario_started",
                            "scenario_id": scenario.id,
                            "run_id": run.run_id,
                            "name": scenario.name,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    )
                    loop.close()
                except Exception as e:
                    logger.error(f"Failed to send WebSocket update: {str(e)}")
            
            threading.Thread(target=send_start_update, daemon=True).start()
            
            # Prepare data
            series = None
            if scenario.parameters and scenario.parameters.get("csv_path"):
                series = prepare_series(path=scenario.parameters.get("csv_path"))
            else:
                series = prepare_series()
            
            # Run simulation with cancellation checks
            result = SimulationEngine.run_simulation(db, scenario, run, series)
            
            # Update scenario on success
            scenario.status = ScenarioStatus.COMPLETED
            scenario.progress = 100.0
            scenario.last_run_at = datetime.utcnow()
            scenario.last_run_status = "completed"
            scenario.last_run_output = {
                "message": "Scenario executed successfully",
                "metrics": {
                    "demand_impact": result.demand_impact,
                    "inventory_impact": result.inventory_impact,
                    "revenue_impact": result.revenue_impact,
                    "stockout_risk": result.stockout_risk
                }
            }
            
            # Update run
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            db.commit()
            
            # Send completion notification
            if user_id:
                NotificationService.create_notification(
                    db=db,
                    user_id=user_id,
                    title=f"✅ Simulation Complete: {scenario.name}",
                    message=f"Simulation for '{scenario.name}' completed successfully in {run.duration_seconds:.2f} seconds.",
                    notification_type="scenario",
                    priority="success"
                )
            
            # Send WebSocket completion update
            def send_complete_update():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        manager.send_dashboard_update({
                            "type": "scenario_completed",
                            "scenario_id": scenario.id,
                            "name": scenario.name,
                            "metrics": {
                                "demand_impact": result.demand_impact,
                                "inventory_impact": result.inventory_impact,
                                "revenue_impact": result.revenue_impact,
                                "stockout_risk": result.stockout_risk
                            },
                            "duration": run.duration_seconds,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    )
                    loop.close()
                except Exception as e:
                    logger.error(f"Failed to send WebSocket update: {str(e)}")
            
            threading.Thread(target=send_complete_update, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Background simulation failed for run {run_id}: {str(e)}")
            
            try:
                # Refresh objects
                scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
                run = db.query(ScenarioRun).filter(ScenarioRun.run_id == run_id).first()
                
                if scenario and run:
                    scenario.status = ScenarioStatus.FAILED
                    scenario.last_run_status = "failed"
                    scenario.last_run_at = datetime.utcnow()
                    scenario.last_run_output = {
                        "message": "Scenario execution failed",
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                    
                    run.status = "failed"
                    run.error_message = str(e)
                    run.completed_at = datetime.utcnow()
                    db.commit()
                    
                    if user_id:
                        NotificationService.create_notification(
                            db=db,
                            user_id=user_id,
                            title=f"❌ Simulation Failed: {scenario.name}",
                            message=f"Simulation for '{scenario.name}' failed: {str(e)}",
                            notification_type="scenario",
                            priority="error"
                        )
            except Exception as inner_e:
                logger.error(f"Failed to update failed status: {str(inner_e)}")
        finally:
            db.close()
    
    # ============= Legacy Sync Run (Deprecated) =============
    
    @staticmethod
    def run_scenario(db: Session, scenario_id: int, user_id: int = None) -> Optional[ScenarioRun]:
        """
        Legacy synchronous run - kept for backward compatibility.
        Use run_scenario_async for production.
        """
        from fastapi import BackgroundTasks
        background_tasks = BackgroundTasks()
        return ScenarioService.run_scenario_async(db, scenario_id, background_tasks, user_id)
    
    # ============= Cancel Run =============
    
    @staticmethod
    def cancel_run(db: Session, run_id: str) -> bool:
        """Cancel a running simulation."""
        run = db.query(ScenarioRun).filter(ScenarioRun.run_id == run_id).first()
        if not run:
            return False
        
        if run.status in ["queued", "running"]:
            run.status = "cancelled"
            run.completed_at = datetime.utcnow()
            db.commit()
            
            # Update scenario
            scenario = ScenarioService.get_scenario_by_id(db, run.scenario_id)
            if scenario and scenario.status == ScenarioStatus.RUNNING:
                scenario.status = ScenarioStatus.CANCELLED
                scenario.progress = 0.0
                db.commit()
            
            # Send notification
            if run.user_id:
                NotificationService.create_notification(
                    db=db,
                    user_id=run.user_id,
                    title=f"⏹️ Simulation Cancelled: {scenario.name}",
                    message=f"Simulation for '{scenario.name}' was cancelled.",
                    notification_type="scenario",
                    priority="warning"
                )
            
            return True
        
        return False
    
    # ============= Retry Run =============
    
    @staticmethod
    def retry_run(db: Session, run_id: str, user_id: int = None, background_tasks: BackgroundTasks = None) -> Optional[ScenarioRun]:
        """Retry a failed simulation."""
        old_run = db.query(ScenarioRun).filter(ScenarioRun.run_id == run_id).first()
        if not old_run:
            return None
        
        # Send retry notification
        if user_id:
            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                title=f"🔄 Simulation Retry Started",
                message=f"Retrying simulation for scenario ID {old_run.scenario_id}",
                notification_type="scenario",
                priority="info"
            )
        
        return ScenarioService.run_scenario_async(db, old_run.scenario_id, background_tasks, user_id)
    
    # ============= Progress =============
    
    @staticmethod
    def get_progress(db: Session, run_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation progress."""
        run = db.query(ScenarioRun).filter(ScenarioRun.run_id == run_id).first()
        if not run:
            return None
        
        return {
            "run_id": run.run_id,
            "status": run.status,
            "progress": run.progress,
            "current_step": run.current_step,
            "step_number": run.step_number,
            "total_steps": run.total_steps,
            "logs": run.logs,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "estimated_completion": run.estimated_completion,
            "duration_seconds": run.duration_seconds
        }
    
    # ============= History =============
    
    @staticmethod
    def get_scenario_history(db: Session, scenario_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a scenario."""
        runs = db.query(ScenarioRun).filter(
            ScenarioRun.scenario_id == scenario_id
        ).order_by(desc(ScenarioRun.created_at)).limit(limit).all()
        
        history = []
        for run in runs:
            history.append({
                "run_id": run.run_id,
                "status": run.status,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "duration_seconds": run.duration_seconds,
                "progress": run.progress,
                "error_message": run.error_message,
                "created_by": run.user_id,
                "created_at": run.created_at
            })
        
        return history
    
    # ============= Metrics =============
    
    @staticmethod
    def get_metrics(db: Session, scenario_id: int) -> Optional[Dict[str, Any]]:
        """Get scenario metrics with optimized query."""
        result = db.query(ScenarioResult).filter(
            ScenarioResult.scenario_id == scenario_id
        ).order_by(desc(ScenarioResult.created_at)).first()
        
        if not result:
            return None
        
        return {
            "demand_impact": result.demand_impact,
            "inventory_impact": result.inventory_impact,
            "revenue_impact": result.revenue_impact,
            "stockout_risk": result.stockout_risk,
            "total_demand": result.total_demand,
            "total_inventory": result.total_inventory,
            "total_revenue": result.total_revenue,
            "stockout_count": result.stockout_count
        }
    
    # ============= Recommendations =============
    
    @staticmethod
    def get_recommendations(db: Session, scenario_id: int) -> List[Dict[str, Any]]:
        """Get full recommendation details for a scenario."""
        result = db.query(ScenarioResult).filter(
            ScenarioResult.scenario_id == scenario_id
        ).order_by(desc(ScenarioResult.created_at)).first()
        
        if not result or not result.recommendation_ids:
            return []
        
        from fastapi_app.models.recommendation_model import Recommendation
        
        recs = db.query(Recommendation).filter(
            Recommendation.id.in_(result.recommendation_ids)
        ).all()
        
        return [
            {
                "id": r.id,
                "sku": r.sku,
                "title": r.title,
                "description": r.description,
                "priority": r.priority.value if hasattr(r.priority, 'value') else str(r.priority),
                "recommendation_type": r.recommendation_type.value if hasattr(r.recommendation_type, 'value') else str(r.recommendation_type),
                "ai_confidence": r.ai_confidence,
                "estimated_savings": r.estimated_savings,
                "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                "action_label": r.action_label,
                "created_at": r.created_at
            }
            for r in recs
        ]
    
    # ============= Dashboard Analytics =============
    
    @staticmethod
    def get_dashboard_analytics(db: Session) -> Dict[str, Any]:
        """Get comprehensive dashboard analytics."""
        from sqlalchemy import func
        
        # Base counts
        total = db.query(func.count(Scenario.id)).scalar() or 0
        completed = db.query(func.count(Scenario.id)).filter(
            Scenario.status == ScenarioStatus.COMPLETED
        ).scalar() or 0
        running = db.query(func.count(Scenario.id)).filter(
            Scenario.status == ScenarioStatus.RUNNING
        ).scalar() or 0
        failed = db.query(func.count(Scenario.id)).filter(
            Scenario.status == ScenarioStatus.FAILED
        ).scalar() or 0
        cancelled = db.query(func.count(Scenario.id)).filter(
            Scenario.status == ScenarioStatus.CANCELLED
        ).scalar() or 0
        
        # Time-based counts
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=7)
        month_start = today - timedelta(days=30)
        
        today_runs = db.query(func.count(ScenarioRun.id)).filter(
            ScenarioRun.created_at >= today
        ).scalar() or 0
        
        week_runs = db.query(func.count(ScenarioRun.id)).filter(
            ScenarioRun.created_at >= week_start
        ).scalar() or 0
        
        month_runs = db.query(func.count(ScenarioRun.id)).filter(
            ScenarioRun.created_at >= month_start
        ).scalar() or 0
        
        # Average metrics from results
        results = db.query(ScenarioResult).all()
        if results:
            avg_revenue = sum(r.total_revenue or 0 for r in results) / len(results)
            avg_demand = sum(r.total_demand or 0 for r in results) / len(results)
            avg_inventory = sum(r.total_inventory or 0 for r in results) / len(results)
            avg_risk = sum(r.stockout_risk or 0 for r in results) / len(results)
            avg_duration = sum(r.run.duration_seconds or 0 for r in results if r.run) / len(results) if results else 0
        else:
            avg_revenue = avg_demand = avg_inventory = avg_risk = avg_duration = 0
        
        # Success rate
        success_rate = (completed / total * 100) if total > 0 else 0
        
        # Top performing scenario
        top_scenario = db.query(Scenario).filter(
            Scenario.status == ScenarioStatus.COMPLETED
        ).order_by(desc(Scenario.progress)).first()
        
        # Highest revenue scenario
        highest_revenue_result = db.query(ScenarioResult).order_by(
            desc(ScenarioResult.total_revenue)
        ).first()
        highest_revenue_scenario = None
        if highest_revenue_result:
            highest_revenue_scenario = ScenarioService.get_scenario_by_id(db, highest_revenue_result.scenario_id)
        
        # Lowest risk scenario
        lowest_risk_result = db.query(ScenarioResult).order_by(
            ScenarioResult.stockout_risk
        ).first()
        lowest_risk_scenario = None
        if lowest_risk_result:
            lowest_risk_scenario = ScenarioService.get_scenario_by_id(db, lowest_risk_result.scenario_id)
        
        # Most executed scenario
        most_executed = db.query(
            ScenarioRun.scenario_id,
            func.count(ScenarioRun.id).label('run_count')
        ).group_by(ScenarioRun.scenario_id).order_by(
            desc('run_count')
        ).first()
        most_executed_scenario = None
        if most_executed:
            most_executed_scenario = ScenarioService.get_scenario_by_id(db, most_executed.scenario_id)
        
        # Top forecast model
        top_model = db.query(
            Scenario.forecast_model,
            func.count(Scenario.id).label('count')
        ).group_by(Scenario.forecast_model).order_by(
            desc('count')
        ).first()
        
        # Top warehouse
        top_warehouse = db.query(
            Scenario.warehouse,
            func.count(Scenario.id).label('count')
        ).filter(Scenario.warehouse.isnot(None)).group_by(
            Scenario.warehouse
        ).order_by(desc('count')).first()
        
        # Top region
        top_region = db.query(
            Scenario.region,
            func.count(Scenario.id).label('count')
        ).filter(Scenario.region.isnot(None)).group_by(
            Scenario.region
        ).order_by(desc('count')).first()
        
        return {
            "total_scenarios": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "cancelled": cancelled,
            "today_simulations": today_runs,
            "week_simulations": week_runs,
            "month_simulations": month_runs,
            "average_revenue": round(avg_revenue, 2),
            "average_demand": round(avg_demand, 2),
            "average_inventory": round(avg_inventory, 2),
            "average_risk": round(avg_risk, 2),
            "average_run_time": round(avg_duration, 2),
            "success_rate": round(profit_margin, 2),
            "top_performing_scenario": {
                "id": top_scenario.id,
                "name": top_scenario.name
            } if top_scenario else None,
            "highest_revenue_scenario": {
                "id": highest_revenue_scenario.id,
                "name": highest_revenue_scenario.name,
                "revenue": highest_revenue_result.total_revenue
            } if highest_revenue_scenario else None,
            "lowest_risk_scenario": {
                "id": lowest_risk_scenario.id,
                "name": lowest_risk_scenario.name,
                "risk": lowest_risk_result.stockout_risk
            } if lowest_risk_scenario else None,
            "most_executed_scenario": {
                "id": most_executed_scenario.id,
                "name": most_executed_scenario.name,
                "executions": most_executed.run_count
            } if most_executed_scenario else None,
            "top_forecast_model": {
                "model": top_model[0],
                "count": top_model[1]
            } if top_model else None,
            "top_warehouse": {
                "warehouse": top_warehouse[0],
                "count": top_warehouse[1]
            } if top_warehouse else None,
            "top_region": {
                "region": top_region[0],
                "count": top_region[1]
            } if top_region else None
        }