# fastapi_app/services/scenario/scenario_service.py
"""
Scenario Service - CRUD and dashboard operations.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from fastapi import BackgroundTasks

from fastapi_app.models.scenario_model import Scenario, ScenarioStatus, ScenarioRun, ScenarioResult
from fastapi_app.models.recommendation_result_model import RecommendationResult
from fastapi_app.schemas.scenario_schema import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioFilter,
    RecommendationResponse
)
from fastapi_app.services.scenario.simulation_engine import SimulationEngine
from fastapi_app.services.forecast.forecast_service import prepare_series
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class ScenarioService:
    """Service for scenario operations."""
    
    # ============= CRUD =============
    
    @staticmethod
    def get_all_scenarios(
        db: Session,
        filter_params: Optional[ScenarioFilter] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get scenarios with filters and pagination."""
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
        """Get a scenario by ID."""
        return db.query(Scenario).filter(Scenario.id == scenario_id).first()
    
    @staticmethod
    def create_scenario(db: Session, scenario_create: ScenarioCreate, user_id: int = None) -> Scenario:
        """Create a new scenario."""
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
    def update_scenario(db: Session, scenario_id: int, scenario_update: ScenarioUpdate) -> Optional[Scenario]:
        """Update a scenario."""
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
        """Delete a scenario."""
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return False
        
        db.delete(scenario)
        db.commit()
        return True
    
    # ============= RUN SIMULATION =============
    
    @staticmethod
    def run_scenario_async(
        db: Session,
        scenario_id: int,
        background_tasks: BackgroundTasks,
        user_id: int = None
    ) -> Optional[ScenarioRun]:
        """Start a scenario simulation asynchronously."""
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return None
        
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
        
        # Start background task
        background_tasks.add_task(
            SimulationEngine.run_simulation_background,
            scenario_id,
            run_id,
            user_id
        )
        
        return run
    
    # ============= PROGRESS =============
    
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
            "message": run.logs[-1]["message"] if run.logs else None,
            "started_at": run.started_at
        }
    
    # ============= DASHBOARD =============
    
    @staticmethod
    def get_dashboard(db: Session, scenario_id: int) -> Optional[Dict[str, Any]]:
        """Get complete dashboard data."""
        result = db.query(ScenarioResult).filter(
            ScenarioResult.scenario_id == scenario_id
        ).order_by(desc(ScenarioResult.created_at)).first()
        
        if not result:
            return None
        
        # Get recommendations
        recommendations = []
        if result.recommendation_ids:
            recs = db.query(RecommendationResult).filter(
                RecommendationResult.id.in_(result.recommendation_ids)
            ).all()
            recommendations = [
                RecommendationResponse(
                    id=r.id,
                    sku=r.sku,
                    title=r.title,
                    description=r.description,
                    priority=r.priority.value if hasattr(r.priority, 'value') else str(r.priority),
                    recommendation_type=r.recommendation_type.value if hasattr(r.recommendation_type, 'value') else str(r.recommendation_type),
                    ai_confidence=r.ai_confidence,
                    estimated_savings=r.estimated_savings,
                    action_label=r.action_label
                )
                for r in recs
            ]
        
        return {
            "summary_cards": result.summary_cards or {
                "demand_impact": result.demand_impact,
                "inventory_impact": result.inventory_impact,
                "revenue_impact": result.revenue_impact,
                "stockout_risk": result.stockout_risk,
                "total_demand": result.total_demand,
                "total_inventory": result.total_inventory,
                "total_revenue": result.total_revenue,
                "stockout_count": result.stockout_count
            },
            "forecast": {
                "labels": result.forecast_labels,
                "baseline": result.forecast_baseline,
                "simulation": result.forecast_simulation
            },
            "inventory": {
                "labels": result.inventory_labels,
                "baseline": result.inventory_baseline,
                "simulation": result.inventory_simulation
            },
            "stockouts": result.stockout_skus or [],
            "recommendations": recommendations
        }
    
    @staticmethod
    def get_forecast_chart(db: Session, scenario_id: int) -> Optional[Dict[str, Any]]:
        """Get forecast chart data."""
        result = db.query(ScenarioResult).filter(
            ScenarioResult.scenario_id == scenario_id
        ).order_by(desc(ScenarioResult.created_at)).first()
        
        if not result:
            return None
        
        return {
            "labels": result.forecast_labels,
            "baseline": result.forecast_baseline,
            "simulation": result.forecast_simulation
        }
    
    @staticmethod
    def get_inventory_chart(db: Session, scenario_id: int) -> Optional[Dict[str, Any]]:
        """Get inventory chart data."""
        result = db.query(ScenarioResult).filter(
            ScenarioResult.scenario_id == scenario_id
        ).order_by(desc(ScenarioResult.created_at)).first()
        
        if not result:
            return None
        
        return {
            "labels": result.inventory_labels,
            "baseline": result.inventory_baseline,
            "simulation": result.inventory_simulation
        }
    
    @staticmethod
    def get_stockouts(db: Session, scenario_id: int) -> List[Dict[str, Any]]:
        """Get stockout table data."""
        result = db.query(ScenarioResult).filter(
            ScenarioResult.scenario_id == scenario_id
        ).order_by(desc(ScenarioResult.created_at)).first()
        
        if not result or not result.stockout_skus:
            return []
        
        return result.stockout_skus
    
    @staticmethod
    def get_recommendations(db: Session, scenario_id: int) -> List[RecommendationResponse]:
        """Get recommendations for a scenario."""
        result = db.query(ScenarioResult).filter(
            ScenarioResult.scenario_id == scenario_id
        ).order_by(desc(ScenarioResult.created_at)).first()
        
        if not result or not result.recommendation_ids:
            return []
        
        recs = db.query(RecommendationResult).filter(
            RecommendationResult.id.in_(result.recommendation_ids)
        ).all()
        
        return [
            RecommendationResponse(
                id=r.id,
                sku=r.sku,
                title=r.title,
                description=r.description,
                priority=r.priority.value if hasattr(r.priority, 'value') else str(r.priority),
                recommendation_type=r.recommendation_type.value if hasattr(r.recommendation_type, 'value') else str(r.recommendation_type),
                ai_confidence=r.ai_confidence,
                estimated_savings=r.estimated_savings,
                action_label=r.action_label
            )
            for r in recs
        ]