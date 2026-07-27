# fastapi_app/services/scenario/comparison_service.py
"""
Comparison Service - Compares multiple scenarios.
"""
from typing import List, Dict, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastapi_app.models.scenario_model import ScenarioComparison, ScenarioResult
from fastapi_app.services.scenario.scenario_service import ScenarioService


class ComparisonService:
    """Service for comparing scenarios."""
    
    @staticmethod
    def compare_scenarios(db: Session, scenario_ids: List[int]) -> Dict[str, Any]:
        """Compare multiple scenarios and return winner and ranking."""
        scenarios = []
        metrics_list = []
        
        for sid in scenario_ids:
            scenario = ScenarioService.get_scenario_by_id(db, sid)
            if not scenario:
                continue
            
            result = db.query(ScenarioResult).filter(
                ScenarioResult.scenario_id == sid
            ).order_by(desc(ScenarioResult.created_at)).first()
            
            if result:
                scenarios.append(scenario)
                metrics_list.append({
                    "scenario_id": sid,
                    "name": scenario.name,
                    "metrics": {
                        "demand_impact": result.demand_impact or 0,
                        "inventory_impact": result.inventory_impact or 0,
                        "revenue_impact": result.revenue_impact or 0,
                        "stockout_risk": result.stockout_risk or 0
                    }
                })
        
        if len(scenarios) < 2:
            return {"error": "Need at least 2 valid scenarios with results"}
        
        # Calculate scores
        scores = {}
        for item in metrics_list:
            metrics = item["metrics"]
            score = (
                metrics.get("demand_impact", 0) * 0.25 +
                -(metrics.get("inventory_impact", 0)) * 0.15 +
                metrics.get("revenue_impact", 0) * 0.35 +
                -(metrics.get("stockout_risk", 0)) * 0.25
            )
            scores[item["scenario_id"]] = score
        
        # Sort by score descending
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        best_scenario_id = sorted_scores[0][0] if sorted_scores else None
        
        # Build ranking
        ranking = []
        for i, (sid, score) in enumerate(sorted_scores):
            scenario = next((s for s in scenarios if s.id == sid), None)
            if scenario:
                metrics = next((m["metrics"] for m in metrics_list if m["scenario_id"] == sid), {})
                ranking.append({
                    "rank": i + 1,
                    "scenario_id": sid,
                    "name": scenario.name,
                    "score": round(score, 2),
                    "metrics": metrics
                })
        
        # Generate comparison chart
        comparison_chart = ComparisonService._generate_comparison_chart(metrics_list)
        
        # Find metric winners
        demand_winner = max(metrics_list, key=lambda x: x["metrics"].get("demand_impact", 0))
        revenue_winner = max(metrics_list, key=lambda x: x["metrics"].get("revenue_impact", 0))
        inventory_winner = min(metrics_list, key=lambda x: x["metrics"].get("inventory_impact", 0))
        risk_winner = min(metrics_list, key=lambda x: x["metrics"].get("stockout_risk", 0))
        
        # Save comparison
        comparison_id = str(uuid.uuid4())
        comparison = ScenarioComparison(
            comparison_id=comparison_id,
            scenario_ids=scenario_ids,
            best_scenario_id=best_scenario_id,
            comparison_summary={
                "ranking": ranking,
                "winner": {
                    "id": best_scenario_id,
                    "name": next((s.name for s in scenarios if s.id == best_scenario_id), None),
                    "score": scores.get(best_scenario_id, 0)
                },
                "metric_winners": {
                    "highest_demand": {
                        "id": demand_winner["scenario_id"],
                        "name": demand_winner["name"],
                        "value": demand_winner["metrics"].get("demand_impact", 0)
                    },
                    "highest_revenue": {
                        "id": revenue_winner["scenario_id"],
                        "name": revenue_winner["name"],
                        "value": revenue_winner["metrics"].get("revenue_impact", 0)
                    },
                    "lowest_inventory": {
                        "id": inventory_winner["scenario_id"],
                        "name": inventory_winner["name"],
                        "value": inventory_winner["metrics"].get("inventory_impact", 0)
                    },
                    "lowest_risk": {
                        "id": risk_winner["scenario_id"],
                        "name": risk_winner["name"],
                        "value": risk_winner["metrics"].get("stockout_risk", 0)
                    }
                }
            },
            comparison_chart=comparison_chart
        )
        db.add(comparison)
        db.commit()
        db.refresh(comparison)
        
        return {
            "comparison_id": comparison_id,
            "winner": comparison.comparison_summary["winner"],
            "ranking": ranking,
            "comparison_chart": comparison_chart,
            "scenario_names": [s.name for s in scenarios],
            "created_at": comparison.created_at
        }
    
    @staticmethod
    def _generate_comparison_chart(metrics_list: List[Dict]) -> Dict[str, Any]:
        """Generate comparison chart data."""
        labels = ["Demand Impact", "Inventory Impact", "Revenue Impact", "Stockout Risk"]
        chart_data = {
            "labels": labels,
            "baseline": [0, 0, 0, 0],
            "scenarios": {}
        }
        
        for item in metrics_list:
            metrics = item["metrics"]
            chart_data["scenarios"][item["name"]] = [
                metrics.get("demand_impact", 0),
                metrics.get("inventory_impact", 0),
                metrics.get("revenue_impact", 0),
                metrics.get("stockout_risk", 0)
            ]
        
        return chart_data