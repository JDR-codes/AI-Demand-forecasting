# fastapi_app/services/scenario/simulation_engine.py
"""
Simulation Engine - Realistic supply chain simulation with WebSocket progress broadcasting.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from fastapi_app.models.scenario_model import Scenario, ScenarioResult, ScenarioRun
from fastapi_app.services.forecast.forecast_service import prepare_series
from fastapi_app.services.recommendation.recommendation_generator_service import RecommendationGeneratorService
from fastapi_app.services.websocket.websocket_manager import manager

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Realistic supply chain simulation engine with WebSocket progress."""
    
    STEPS = [
        (1, "Loading Data", "loading"),
        (2, "Running Forecast", "forecast"),
        (3, "Demand Simulation", "demand"),
        (4, "Inventory Simulation", "inventory"),
        (5, "Revenue Simulation", "revenue"),
        (6, "Stockout Simulation", "stockout"),
        (7, "Generating Recommendations", "recommendations"),
        (8, "Saving Results", "saving"),
    ]
    
    @staticmethod
    def _check_cancelled(db: Session, run: ScenarioRun) -> bool:
        """Check if the run has been cancelled."""
        db.refresh(run)
        if run.status == "cancelled":
            return True
        return False
    
    @staticmethod
    async def _broadcast_progress(
        run: ScenarioRun,
        scenario: Scenario,
        message: str = None
    ):
        """Broadcast progress update via WebSocket."""
        try:
            await manager.send_progress_update(
                channel=f"scenario_{run.run_id}",
                job_id=run.run_id,
                progress=run.progress,
                step=run.current_step or "Processing",
                status=run.status,
                remaining_time=None,
                metadata={
                    "scenario_id": scenario.id,
                    "scenario_name": scenario.name,
                    "step_number": run.step_number,
                    "total_steps": run.total_steps,
                    "logs": run.logs[-1] if run.logs else None,
                    "estimated_completion": run.estimated_completion.isoformat() if run.estimated_completion else None
                }
            )
            
            # Also broadcast to dashboard channel
            await manager.send_dashboard_update({
                "type": "simulation_progress",
                "run_id": run.run_id,
                "scenario_id": scenario.id,
                "scenario_name": scenario.name,
                "progress": run.progress,
                "step": run.current_step,
                "step_number": run.step_number,
                "total_steps": run.total_steps,
                "logs": run.logs[-1] if run.logs else None,
                "estimated_completion": run.estimated_completion.isoformat() if run.estimated_completion else None,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to broadcast progress: {str(e)}")
    
    @staticmethod
    def _broadcast_progress_sync(
        db: Session,
        run: ScenarioRun,
        scenario: Scenario
    ):
        """Synchronous wrapper for broadcasting progress."""
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                SimulationEngine._broadcast_progress(run, scenario)
            )
            loop.close()
        except Exception as e:
            logger.error(f"Failed to broadcast progress sync: {str(e)}")
    
    @staticmethod
    def run_simulation(
        db: Session,
        scenario: Scenario,
        run: ScenarioRun,
        series: pd.Series
    ) -> ScenarioResult:
        """
        Run the full simulation pipeline with WebSocket progress broadcasting.
        """
        total_steps = len(SimulationEngine.STEPS)
        run.total_steps = total_steps
        start_time = datetime.utcnow()
        
        # Step 1: Load Data
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[0]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 5.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Loading data...")
        run.estimated_completion = start_time + timedelta(seconds=60)
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        # Step 2: Forecast
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[1]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 15.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Running forecast...")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        forecast_values = SimulationEngine._run_forecast(scenario, series)
        forecast_labels = SimulationEngine._generate_labels(len(forecast_values))
        run.progress = 25.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", f"Forecast generated with {len(forecast_values)} points")
        run.estimated_completion = datetime.utcnow() + timedelta(seconds=45)
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        # Step 3: Demand Simulation
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[2]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 35.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Simulating demand with seasonality and trends...")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        demand_impact, demand_simulation = SimulationEngine._simulate_demand_advanced(scenario, forecast_values)
        run.progress = 45.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", f"Demand impact: {demand_impact}%")
        run.estimated_completion = datetime.utcnow() + timedelta(seconds=35)
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        # Step 4: Inventory Simulation
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[3]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 50.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Simulating inventory with safety stock and lead time...")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        inventory_impact, inventory_simulation, safety_stock, reorder_points = SimulationEngine._simulate_inventory_advanced(
            scenario, demand_simulation
        )
        run.progress = 60.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", f"Inventory impact: {inventory_impact}%")
        run.estimated_completion = datetime.utcnow() + timedelta(seconds=25)
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        # Step 5: Revenue Simulation
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[4]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 65.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Simulating revenue and profit...")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        revenue_impact, total_revenue, total_profit, profit_margin = SimulationEngine._simulate_revenue_advanced(
            scenario, demand_simulation, inventory_simulation
        )
        run.progress = 75.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", f"Revenue impact: {revenue_impact}%")
        run.estimated_completion = datetime.utcnow() + timedelta(seconds=15)
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        # Step 6: Stockout Simulation
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[5]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 80.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Simulating stockout risk and lost sales...")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        stockout_risk, stockout_skus, stockout_count, lost_sales, recovery_days = SimulationEngine._simulate_stockout_advanced(
            scenario, demand_simulation, demand_impact, inventory_simulation, safety_stock
        )
        run.progress = 85.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", f"Stockout risk: {stockout_risk}%, {stockout_count} SKUs at risk")
        run.estimated_completion = datetime.utcnow() + timedelta(seconds=10)
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        # Step 7: Generate Recommendations
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[6]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 90.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Generating recommendations...")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        recommendation_ids = SimulationEngine._generate_recommendations(db, scenario, demand_simulation)
        run.progress = 95.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", f"Generated {len(recommendation_ids)} recommendations")
        run.estimated_completion = datetime.utcnow() + timedelta(seconds=5)
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        # Step 8: Create Result
        if SimulationEngine._check_cancelled(db, run):
            return None
        
        step_num, step_name, step_key = SimulationEngine.STEPS[7]
        run.step_number = step_num
        run.current_step = step_name
        run.progress = 97.0
        run.logs = SimulationEngine._add_log(run.logs, "INFO", "Saving results...")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        result = SimulationEngine._create_result_advanced(
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
            reorder_points=reorder_points,
            revenue_impact=revenue_impact,
            total_revenue=total_revenue,
            total_profit=total_profit,
            profit_margin=profit_margin,
            stockout_risk=stockout_risk,
            stockout_skus=stockout_skus,
            stockout_count=stockout_count,
            lost_sales=lost_sales,
            recovery_days=recovery_days,
            recommendation_ids=recommendation_ids
        )
        
        # Update run completion
        run.progress = 100.0
        run.step_number = total_steps
        run.current_step = "Completed"
        run.completed_at = datetime.utcnow()
        run.duration_seconds = (run.completed_at - start_time).total_seconds()
        run.logs = SimulationEngine._add_log(run.logs, "INFO", f"Simulation completed in {run.duration_seconds:.2f} seconds")
        db.commit()
        SimulationEngine._broadcast_progress_sync(db, run, scenario)
        
        return result
    
    @staticmethod
    def _add_log(logs: Optional[List], level: str, message: str) -> List:
        """Add a log entry."""
        if logs is None:
            logs = []
        logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        })
        return logs
    
    @staticmethod
    def _generate_labels(length: int) -> List[str]:
        """Generate date labels for charts."""
        start_date = datetime.utcnow()
        return [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(length)]
    
    @staticmethod
    def _run_forecast(scenario: Scenario, series: pd.Series) -> List[float]:
        """Run forecast based on scenario configuration."""
        from fastapi_app.ai.arima import forecast as arima_forecast, train_arima
        from fastapi_app.ai.xgboost_model import forecast_xgboost
        from fastapi_app.ai.lstm import forecast_lstm
        from fastapi_app.ai.prophet import forecast_prophet
        
        model_type = scenario.forecast_model or "arima"
        horizon = scenario.time_horizon or 30
        
        series_list = series.tolist()
        
        try:
            if model_type == "arima":
                model = train_arima(series_list, order=(1, 1, 1))
                forecast = arima_forecast(model, horizon)
            elif model_type == "xgboost":
                forecast = forecast_xgboost(None, series_list, steps=horizon, n_lags=7)
            elif model_type == "lstm":
                forecast = forecast_lstm(None, series_list, steps=horizon, n_lags=7)
            elif model_type == "prophet":
                try:
                    forecast = forecast_prophet(None, periods=horizon)
                except:
                    model = train_arima(series_list, order=(1, 1, 1))
                    forecast = arima_forecast(model, horizon)
            else:
                model = train_arima(series_list, order=(1, 1, 1))
                forecast = arima_forecast(model, horizon)
        except Exception as e:
            logger.error(f"Forecast failed: {str(e)}")
            last_value = series_list[-1] if series_list else 100
            forecast = [last_value * (1 + i * 0.01) for i in range(horizon)]
        
        return forecast
    
    @staticmethod
    def _simulate_demand_advanced(scenario: Scenario, forecast: List[float]) -> Tuple[float, List[float]]:
        """Advanced demand simulation with seasonality, trends, and promotions."""
        if not forecast:
            return 0, []
        
        base = sum(forecast) / len(forecast)
        
        surge = 1 + (scenario.demand_surge or 0) / 100
        seasonal = 1 + (scenario.seasonal_impact or 0) / 100
        growth_trend = 1.02
        promotion_impact = 1 + (scenario.discount or 0) / 300
        festival_impact = 1.05
        
        impact_factor = surge * seasonal * growth_trend * promotion_impact * festival_impact
        demand_impact = round((impact_factor - 1) * 100, 2)
        
        demand_simulation = []
        for i, v in enumerate(forecast):
            week_factor = 1 + 0.1 * (1 if i % 7 in [5, 6] else 0)
            demand_simulation.append(v * impact_factor * week_factor)
        
        return demand_impact, demand_simulation
    
    @staticmethod
    def _simulate_inventory_advanced(
        scenario: Scenario,
        demand_simulation: List[float]
    ) -> Tuple[float, List[float], float, List[float]]:
        """Advanced inventory simulation with safety stock and reorder points."""
        if not demand_simulation:
            return 0, [], 0, []
        
        opening_inventory = 500
        safety_stock = opening_inventory * 0.25
        lead_time = scenario.supply_delay or 3
        reorder_point = safety_stock + (sum(demand_simulation) / len(demand_simulation)) * lead_time
        
        inventory_simulation = []
        reorder_points = []
        current_inventory = opening_inventory
        incoming_orders = []
        
        for i, demand in enumerate(demand_simulation):
            if incoming_orders and i == incoming_orders[0]["delivery_day"]:
                current_inventory += incoming_orders[0]["quantity"]
                incoming_orders.pop(0)
            
            if current_inventory < reorder_point:
                order_qty = reorder_point * 1.5
                delivery_day = i + lead_time
                incoming_orders.append({
                    "quantity": order_qty,
                    "delivery_day": delivery_day
                })
                reorder_points.append({
                    "day": i,
                    "quantity": order_qty,
                    "delivery_day": delivery_day
                })
            
            closing_inventory = current_inventory - demand
            if closing_inventory < 0:
                closing_inventory = 0
            
            inventory_simulation.append(closing_inventory)
            current_inventory = closing_inventory
        
        avg_inventory = sum(inventory_simulation) / len(inventory_simulation) if inventory_simulation else 0
        inventory_impact = round((avg_inventory - opening_inventory) / opening_inventory * 100, 2)
        
        return inventory_impact, inventory_simulation, safety_stock, reorder_points
    
    @staticmethod
    def _simulate_revenue_advanced(
        scenario: Scenario,
        demand_simulation: List[float],
        inventory_simulation: List[float]
    ) -> Tuple[float, float, float, float]:
        """Advanced revenue simulation with profit and margins."""
        unit_price = 30
        unit_cost = 18
        holding_cost_per_unit = 2
        discount_percentage = (scenario.discount or 0) / 100
        price_change_percentage = (scenario.price_change or 0) / 100
        
        total_demand = sum(demand_simulation)
        total_inventory = sum(inventory_simulation)
        
        effective_price = unit_price * (1 + price_change_percentage / 100)
        discounted_price = effective_price * (1 - discount_percentage)
        
        gross_revenue = total_demand * effective_price
        discount_loss = gross_revenue * discount_percentage
        net_revenue = gross_revenue - discount_loss
        
        total_cogs = total_inventory * unit_cost
        total_holding_cost = total_inventory * holding_cost_per_unit
        total_cost = total_cogs + total_holding_cost
        
        total_profit = net_revenue - total_cost
        profit_margin = (total_profit / net_revenue * 100) if net_revenue > 0 else 0
        
        base_revenue = total_demand * unit_price
        revenue_impact = round((net_revenue - base_revenue) / base_revenue * 100, 2)
        
        return revenue_impact, net_revenue, total_profit, profit_margin
    
    @staticmethod
    def _simulate_stockout_advanced(
        scenario: Scenario,
        demand_simulation: List[float],
        demand_impact: float,
        inventory_simulation: List[float],
        safety_stock: float
    ) -> Tuple[float, List[Dict], int, float, int]:
        """Advanced stockout simulation with lost sales and recovery."""
        if not demand_simulation or not inventory_simulation:
            return 0, [], 0, 0, 0
        
        avg_demand = sum(demand_simulation) / len(demand_simulation)
        avg_inventory = sum(inventory_simulation) / len(inventory_simulation)
        
        surge = 1 + (scenario.demand_surge or 0) / 100
        delay = scenario.supply_delay or 0
        
        risk_factor = surge * (1 + delay * 0.05) * (avg_demand / (avg_inventory + 1))
        stockout_risk = min(100, risk_factor * 30 + max(0, demand_impact / 2))
        
        stockout_events = []
        for i, (demand, inventory) in enumerate(zip(demand_simulation, inventory_simulation)):
            if inventory < demand:
                stockout_events.append({
                    "day": i,
                    "lost_sales": demand - inventory,
                    "demand": demand,
                    "inventory": inventory
                })
        
        total_lost_sales = sum(e["lost_sales"] for e in stockout_events)
        lost_revenue = total_lost_sales * 30
        recovery_days = min(30, int(stockout_risk / 3.33))
        
        stockout_skus = []
        sku_count = min(50, max(5, int(stockout_risk / 4)))
        base_sku = scenario.sku or "SKU"
        
        for i in range(sku_count):
            sku_variance = 1 + (i / sku_count) * 0.5
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
        
        return round(stockout_risk, 2), stockout_skus[:20], len([s for s in stockout_skus if s["risk_level"] == "high"]), total_lost_sales, recovery_days
    
    @staticmethod
    def _generate_recommendations(db: Session, scenario: Scenario, demand_simulation: List[float]) -> List[int]:
        """Generate and save recommendations."""
        recommendations = RecommendationGeneratorService.generate_from_forecast(
            db=db,
            forecast_values=demand_simulation,
            k=5,
            sku=scenario.sku,
            region=scenario.region,
            warehouse=scenario.warehouse,
            user_id=scenario.created_by
        )
        
        return [r.id for r in recommendations]
    
    @staticmethod
    def _create_result_advanced(
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
        reorder_points: List[Dict],
        revenue_impact: float,
        total_revenue: float,
        total_profit: float,
        profit_margin: float,
        stockout_risk: float,
        stockout_skus: List[Dict],
        stockout_count: int,
        lost_sales: float,
        recovery_days: int,
        recommendation_ids: List[int]
    ) -> ScenarioResult:
        """Create enhanced scenario result."""
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
            "total_profit": round(total_profit, 2),
            "profit_margin": round(profit_margin, 2),
            "stockout_count": stockout_count,
            "safety_stock": round(safety_stock, 2),
            "lost_sales": round(lost_sales, 2),
            "recovery_days": recovery_days,
            "avg_demand": round(total_demand / len(demand_simulation), 2) if demand_simulation else 0,
            "avg_inventory": round(total_inventory / len(inventory_simulation), 2) if inventory_simulation else 0
        }
        
        all_skus = []
        for i, (forecast, inventory) in enumerate(zip(demand_simulation[:20], inventory_simulation[:20])):
            sku_name = scenario.sku or f"SKU-{i+1:03d}"
            all_skus.append({
                "sku": sku_name,
                "product_name": f"Product {i+1}",
                "forecast": round(forecast, 2),
                "inventory": round(inventory, 2),
                "demand_percentage": round(forecast / total_demand * 100, 2) if total_demand > 0 else 0,
                "inventory_percentage": round(inventory / total_inventory * 100, 2) if total_inventory > 0 else 0,
                "stockout_risk": round(max(0, (forecast - inventory) / forecast * 100), 2) if forecast > 0 else 0
            })
        
        result = ScenarioResult(
            scenario_id=scenario.id,
            run_id=run.id,
            demand_impact=demand_impact,
            inventory_impact=inventory_impact,
            revenue_impact=revenue_impact,
            stockout_risk=stockout_risk,
            stockout_skus=stockout_skus,
            forecast_json=forecast_values,
            inventory_json=inventory_simulation,
            summary_json=summary_cards,
            forecast_labels=forecast_labels,
            forecast_baseline=forecast_values,
            forecast_simulation=demand_simulation,
            forecast_difference=[s - b for s, b in zip(demand_simulation, forecast_values)],
            inventory_labels=forecast_labels,
            inventory_baseline=[500] * len(forecast_values),
            inventory_simulation=inventory_simulation,
            inventory_difference=[s - 500 for s in inventory_simulation],
            all_skus=all_skus,
            recommendation_ids=recommendation_ids,
            summary_cards=summary_cards,
            total_demand=total_demand,
            total_inventory=total_inventory,
            total_revenue=total_revenue,
            stockout_count=stockout_count
        )
        
        db.add(result)
        db.commit()
        db.refresh(result)
        
        return result