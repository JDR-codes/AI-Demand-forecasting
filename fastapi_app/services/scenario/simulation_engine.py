# fastapi_app/services/scenario/simulation_engine.py
"""
Simulation Engine - Runs simulation with simplified progress (5 steps).
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
import numpy as np
import pandas as pd
import asyncio
import traceback

from sqlalchemy.orm import Session

from fastapi_app.models.scenario_model import Scenario, ScenarioResult, ScenarioRun, ScenarioStatus
from fastapi_app.services.forecast.forecast_service import prepare_series
from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Simulation engine with 5-step progress for UI."""
    
    # Simplified 5 steps for UI
    STEPS = [
        (1, "Loading Dataset"),
        (2, "Forecast Generation"),
        (3, "Running Simulation"),
        (4, "Generating Recommendations"),
        (5, "Saving Results"),
    ]
    
    @staticmethod
    def run_simulation_background(scenario_id: int, run_id: str, user_id: int = None):
        """Background task to run simulation with its own session."""
        db = SessionLocal()
        
        try:
            scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            run = db.query(ScenarioRun).filter(ScenarioRun.run_id == run_id).first()
            
            if not scenario or not run:
                logger.error(f"Scenario {scenario_id} or run {run_id} not found")
                return
            
            # Run simulation
            result = SimulationEngine._run_simulation(db, scenario, run)
            
            if result:
                # Update scenario
                scenario.status = ScenarioStatus.COMPLETED
                scenario.progress = 100.0
                scenario.last_run_at = datetime.utcnow()
                scenario.last_run_status = "completed"
                db.commit()
                
                # Broadcast completion
                SimulationEngine._broadcast_completion(db, run, scenario, result)
                
        except Exception as e:
            logger.error(f"Simulation failed for run {run_id}: {str(e)}")
            try:
                scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
                run = db.query(ScenarioRun).filter(ScenarioRun.run_id == run_id).first()
                
                if scenario and run:
                    scenario.status = ScenarioStatus.FAILED
                    scenario.last_run_status = "failed"
                    scenario.last_run_at = datetime.utcnow()
                    
                    run.status = "failed"
                    run.error_message = str(e)
                    run.completed_at = datetime.utcnow()
                    db.commit()
                    
                    SimulationEngine._broadcast_failure(db, run, scenario, str(e))
            except Exception as inner_e:
                logger.error(f"Failed to update failed status: {str(inner_e)}")
        finally:
            db.close()
    
    @staticmethod
    def _run_simulation(db: Session, scenario: Scenario, run: ScenarioRun) -> Optional[ScenarioResult]:
        """Run the simulation pipeline."""
        start_time = datetime.utcnow()
        
        # Step 1: Load Dataset
        if not SimulationEngine._update_step(db, run, scenario, 1):
            return None
        
        series = prepare_series()
        if series is None or len(series) == 0:
            raise ValueError("No data available for simulation")
        
        # Step 2: Forecast Generation
        if not SimulationEngine._update_step(db, run, scenario, 2):
            return None
        
        forecast_values = SimulationEngine._run_forecast(scenario, series)
        forecast_labels = SimulationEngine._generate_labels(len(forecast_values))
        
        # Step 3: Running Simulation (internal steps: demand, discount, price, supply, inventory, revenue, stockout)
        if not SimulationEngine._update_step(db, run, scenario, 3):
            return None
        
        # 3a: Apply Demand Surge
        demand_impact, demand_simulation = SimulationEngine._apply_demand_surge(scenario, forecast_values)
        
        # 3b: Apply Discount and Price Change
        discount_factor = 1 - (scenario.discount / 100)
        price_factor = 1 + (scenario.price_change / 100)
        
        # 3c: Apply Supply Delay
        supply_delay = scenario.supply_delay
        
        # 3d: Inventory Calculation
        inventory_impact, inventory_simulation, safety_stock = SimulationEngine._calculate_inventory(
            scenario, demand_simulation, supply_delay
        )
        
        # 3e: Revenue Calculation
        revenue_impact, total_revenue, total_cost, profit_margin = SimulationEngine._calculate_revenue(
            scenario, demand_simulation, inventory_simulation, price_factor, discount_factor
        )
        
        # 3f: Stockout Detection
        stockout_risk, stockout_skus, stockout_count = SimulationEngine._detect_stockouts(
            scenario, demand_simulation, inventory_simulation, safety_stock
        )
        
        # Step 4: Generate Recommendations
        if not SimulationEngine._update_step(db, run, scenario, 4):
            return None
        
        recommendation_ids = SimulationEngine._generate_recommendations(db, scenario, demand_simulation)
        
        # Step 5: Save Results
        if not SimulationEngine._update_step(db, run, scenario, 5):
            return None
        
        result = SimulationEngine._save_result(
            db=db,
            scenario=scenario,
            run=run,
            forecast_values=forecast_values,
            forecast_labels=forecast_labels,
            demand_impact=demand_impact,
            demand_simulation=demand_simulation,
            inventory_impact=inventory_impact,
            inventory_simulation=inventory_simulation,
            safety_stock=safety_stock,
            revenue_impact=revenue_impact,
            total_revenue=total_revenue,
            total_cost=total_cost,
            profit_margin=profit_margin,
            stockout_risk=stockout_risk,
            stockout_skus=stockout_skus,
            stockout_count=stockout_count,
            recommendation_ids=recommendation_ids
        )
        
        # Update run completion
        run.progress = 100.0
        run.step_number = len(SimulationEngine.STEPS)
        run.current_step = "Completed"
        run.completed_at = datetime.utcnow()
        run.duration_seconds = (run.completed_at - start_time).total_seconds()
        db.commit()
        
        return result
    
    @staticmethod
    def _update_step(db: Session, run: ScenarioRun, scenario: Scenario, step_num: int) -> bool:
        """Update a step and broadcast progress."""
        # Check for cancellation
        db.refresh(run)
        if run.status == "cancelled":
            return False
        
        step_name = SimulationEngine.STEPS[step_num - 1][1]
        
        # Update run
        run.step_number = step_num
        run.current_step = step_name
        run.progress = (step_num / len(SimulationEngine.STEPS)) * 100
        
        # Add log
        if run.logs is None:
            run.logs = []
        run.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": step_name
        })
        
        db.commit()
        
        # Broadcast progress
        SimulationEngine._broadcast_progress(db, run, scenario, step_name)
        
        return True
    
    @staticmethod
    def _broadcast_progress(db: Session, run: ScenarioRun, scenario: Scenario, step_name: str):
        """Broadcast progress via WebSocket."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                manager.send_progress_update(
                    channel=f"scenario_{run.run_id}",
                    job_id=run.run_id,
                    progress=run.progress,
                    step=step_name,
                    status=run.status,
                    remaining_time=None,
                    metadata={
                        "scenario_id": scenario.id,
                        "step_number": run.step_number,
                        "total_steps": run.total_steps
                    }
                )
            )
            loop.close()
        except Exception as e:
            logger.error(f"Failed to broadcast progress: {str(e)}")
    
    @staticmethod
    def _broadcast_completion(db: Session, run: ScenarioRun, scenario: Scenario, result: ScenarioResult):
        """Broadcast completion via WebSocket."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                manager.send_dashboard_update({
                    "type": "scenario_completed",
                    "run_id": run.run_id,
                    "scenario_id": scenario.id,
                    "scenario_name": scenario.name,
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
            logger.error(f"Failed to broadcast completion: {str(e)}")
    
    @staticmethod
    def _broadcast_failure(db: Session, run: ScenarioRun, scenario: Scenario, error: str):
        """Broadcast failure via WebSocket."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                manager.send_dashboard_update({
                    "type": "scenario_failed",
                    "run_id": run.run_id,
                    "scenario_id": scenario.id,
                    "scenario_name": scenario.name,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            loop.close()
        except Exception as e:
            logger.error(f"Failed to broadcast failure: {str(e)}")
    
    @staticmethod
    def _run_forecast(scenario: Scenario, series: pd.Series) -> List[float]:
        """Run forecast based on scenario configuration."""
        from fastapi_app.ai.arima import forecast as arima_forecast, train_arima
        
        horizon = scenario.time_horizon or 30
        series_list = series.tolist()
        
        try:
            model = train_arima(series_list, order=(1, 1, 1))
            forecast = arima_forecast(model, horizon)
        except Exception as e:
            logger.error(f"Forecast failed: {str(e)}")
            last_value = series_list[-1] if series_list else 100
            forecast = [last_value * (1 + i * 0.01) for i in range(horizon)]
        
        return forecast
    
    @staticmethod
    def _apply_demand_surge(scenario: Scenario, forecast: List[float]) -> Tuple[float, List[float]]:
        """Apply demand surge to forecast."""
        if not forecast:
            return 0, []
        
        surge_factor = 1 + (scenario.demand_surge / 100)
        seasonal_factor = 1 + (scenario.seasonal_impact / 100)
        
        total_factor = surge_factor * seasonal_factor
        demand_impact = round((total_factor - 1) * 100, 2)
        
        demand_simulation = [v * total_factor for v in forecast]
        
        return demand_impact, demand_simulation
    
    @staticmethod
    def _calculate_inventory(
        scenario: Scenario,
        demand_simulation: List[float],
        supply_delay: int
    ) -> Tuple[float, List[float], float]:
        """Calculate inventory with safety stock."""
        if not demand_simulation:
            return 0, [], 0
        
        opening_inventory = 500
        safety_stock = opening_inventory * 0.25
        lead_time = supply_delay or 3
        
        inventory_simulation = []
        current_inventory = opening_inventory
        incoming_orders = []
        
        for i, demand in enumerate(demand_simulation):
            # Check for incoming orders
            if incoming_orders and i == incoming_orders[0]["delivery_day"]:
                current_inventory += incoming_orders[0]["quantity"]
                incoming_orders.pop(0)
            
            # Reorder if below safety stock
            if current_inventory < safety_stock:
                order_qty = safety_stock * 2
                delivery_day = i + lead_time + 1
                incoming_orders.append({
                    "quantity": order_qty,
                    "delivery_day": delivery_day
                })
            
            # Apply demand
            closing_inventory = max(0, current_inventory - demand)
            inventory_simulation.append(closing_inventory)
            current_inventory = closing_inventory
        
        avg_inventory = sum(inventory_simulation) / len(inventory_simulation) if inventory_simulation else 0
        inventory_impact = round((avg_inventory - opening_inventory) / opening_inventory * 100, 2)
        
        return inventory_impact, inventory_simulation, safety_stock
    
    @staticmethod
    def _calculate_revenue(
        scenario: Scenario,
        demand_simulation: List[float],
        inventory_simulation: List[float],
        price_factor: float,
        discount_factor: float
    ) -> Tuple[float, float, float, float]:
        """Calculate revenue with price changes and discounts."""
        unit_price = 30
        unit_cost = 18
        holding_cost_per_unit = 2
        
        total_demand = sum(demand_simulation)
        total_inventory = sum(inventory_simulation)
        
        effective_price = unit_price * price_factor * discount_factor
        
        total_revenue = total_demand * effective_price
        total_cogs = total_inventory * unit_cost
        total_holding_cost = total_inventory * holding_cost_per_unit
        total_cost = total_cogs + total_holding_cost
        
        base_revenue = total_demand * unit_price
        revenue_impact = round((total_revenue - base_revenue) / base_revenue * 100, 2)
        
        profit_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
        
        return revenue_impact, total_revenue, total_cost, profit_margin
    
    @staticmethod
    def _detect_stockouts(
        scenario: Scenario,
        demand_simulation: List[float],
        inventory_simulation: List[float],
        safety_stock: float
    ) -> Tuple[float, List[Dict], int]:
        """Detect stockouts and calculate risk."""
        if not demand_simulation or not inventory_simulation:
            return 0, [], 0
        
        avg_demand = sum(demand_simulation) / len(demand_simulation)
        avg_inventory = sum(inventory_simulation) / len(inventory_simulation)
        
        # Calculate risk
        surge = 1 + (scenario.demand_surge / 100)
        delay = scenario.supply_delay or 0
        
        risk_factor = surge * (1 + delay * 0.05) * (avg_demand / (avg_inventory + 1))
        stockout_risk = min(100, risk_factor * 30)
        
        # Identify stockout SKUs
        stockout_skus = []
        base_sku = scenario.sku or "SKU"
        
        for i in range(min(20, int(stockout_risk / 5) + 5)):
            sku_variance = 1 + (i / 20) * 0.5
            sku_demand = avg_demand * sku_variance
            shortage = sku_demand * (surge - 1) * (1 + delay * 0.1)
            revenue_risk = shortage * 30
            
            if shortage > 50 or stockout_risk > 60:
                risk_level = "high"
            elif shortage > 20 or stockout_risk > 30:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            stockout_skus.append({
                "sku": f"{base_sku}-{i+1:03d}",
                "product_name": f"Product {i+1}",
                "demand": round(sku_demand, 2),
                "shortage": round(shortage, 2),
                "revenue_risk": round(revenue_risk, 2),
                "risk_level": risk_level,
                "current_stock": round(max(100, 500 - i * 10), 2),
                "recommended_quantity": round(shortage * 1.2, 2),
                "lost_sales": round(shortage * 0.3, 2)
            })
        
        risk_order = {"high": 0, "medium": 1, "low": 2}
        stockout_skus.sort(key=lambda x: risk_order[x["risk_level"]])
        
        stockout_count = len([s for s in stockout_skus if s["risk_level"] == "high"])
        
        return round(stockout_risk, 2), stockout_skus, stockout_count
    
    @staticmethod
    def _generate_recommendations(db: Session, scenario: Scenario, demand_simulation: List[float]) -> List[int]:
        """Generate recommendations from simulation."""
        # TODO: Integrate with actual recommendation generator
        # For now, return empty list
        return []
    
    @staticmethod
    def _save_result(
        db: Session,
        scenario: Scenario,
        run: ScenarioRun,
        forecast_values: List[float],
        forecast_labels: List[str],
        demand_impact: float,
        demand_simulation: List[float],
        inventory_impact: float,
        inventory_simulation: List[float],
        safety_stock: float,
        revenue_impact: float,
        total_revenue: float,
        total_cost: float,
        profit_margin: float,
        stockout_risk: float,
        stockout_skus: List[Dict],
        stockout_count: int,
        recommendation_ids: List[int]
    ) -> ScenarioResult:
        """Save simulation results."""
        total_demand = sum(demand_simulation)
        total_inventory = sum(inventory_simulation)
        
        summary_cards = {
            "demand_impact": demand_impact,
            "inventory_impact": inventory_impact,
            "revenue_impact": revenue_impact,
            "stockout_risk": stockout_risk,
            "total_demand": round(total_demand, 2),
            "total_inventory": round(total_inventory, 2),
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "profit_margin": round(profit_margin, 2),
            "stockout_count": stockout_count,
            "safety_stock": round(safety_stock, 2)
        }
        
        result = ScenarioResult(
            scenario_id=scenario.id,
            run_id=run.id,
            demand_impact=demand_impact,
            inventory_impact=inventory_impact,
            revenue_impact=revenue_impact,
            stockout_risk=stockout_risk,
            forecast_labels=forecast_labels,
            forecast_baseline=forecast_values,
            forecast_simulation=demand_simulation,
            inventory_labels=forecast_labels,
            inventory_baseline=[500] * len(forecast_values),
            inventory_simulation=inventory_simulation,
            summary_cards=summary_cards,
            stockout_skus=stockout_skus,
            stockout_count=stockout_count,
            recommendation_ids=recommendation_ids,
            total_demand=total_demand,
            total_inventory=total_inventory,
            total_revenue=total_revenue
        )
        
        db.add(result)
        db.commit()
        db.refresh(result)
        
        return result
    
    @staticmethod
    def _generate_labels(length: int) -> List[str]:
        """Generate date labels for charts."""
        start_date = datetime.utcnow()
        return [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(length)]