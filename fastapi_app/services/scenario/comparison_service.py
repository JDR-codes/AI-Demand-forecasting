# fastapi_app/services/scenario/comparison_service.py
from typing import List, Dict, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastapi_app.models.scenario_model import ScenarioComparison
from fastapi_app.services.scenario.scenario_service import ScenarioService


class ComparisonService:
    
    @staticmethod
    def compare_scenarios(db: Session, scenario_ids: List[int]) -> Dict[str, Any]:
        """Compare multiple scenarios with ranking and metric winners."""
        scenarios = []
        metrics_list = []
        
        for sid in scenario_ids:
            scenario = ScenarioService.get_scenario_by_id(db, sid)
            if scenario:
                scenarios.append(scenario)
                metrics = ScenarioService.get_metrics(db, sid)
                metrics_list.append({
                    "scenario_id": sid,
                    "name": scenario.name,
                    "metrics": metrics or {}
                })
        
        if len(scenarios) < 2:
            return {"error": "Need at least 2 valid scenarios"}
        
        # Calculate scores for each scenario
        scores = {}
        for item in metrics_list:
            metrics = item.get("metrics") or {}
            score = (
                (metrics.get("demand_impact") or 0) * 0.25 +
                -(metrics.get("inventory_impact") or 0) * 0.15 +
                (metrics.get("revenue_impact") or 0) * 0.35 +
                -(metrics.get("stockout_risk") or 0) * 0.25
            )
            scores[item["scenario_id"]] = score
        
        # Sort by score descending
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Determine winners
        best_scenario_id = sorted_scores[0][0] if sorted_scores else None
        runner_up_id = sorted_scores[1][0] if len(sorted_scores) > 1 else None
        
        # Metric winners
        demand_winner = max(metrics_list, key=lambda x: x.get("metrics", {}).get("demand_impact", 0))
        revenue_winner = max(metrics_list, key=lambda x: x.get("metrics", {}).get("revenue_impact", 0))
        inventory_winner = min(metrics_list, key=lambda x: x.get("metrics", {}).get("inventory_impact", 0))
        risk_winner = min(metrics_list, key=lambda x: x.get("metrics", {}).get("stockout_risk", 0))
        
        # Ranking list
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
                    "metrics": {
                        "demand_impact": metrics.get("demand_impact", 0),
                        "inventory_impact": metrics.get("inventory_impact", 0),
                        "revenue_impact": metrics.get("revenue_impact", 0),
                        "stockout_risk": metrics.get("stockout_risk", 0)
                    }
                })
        
        # Generate comparison chart
        comparison_chart = ComparisonService._generate_comparison_chart_enhanced(scenarios, metrics_list)
        
        # Create comparison record
        comparison_id = str(uuid.uuid4())
        comparison = ScenarioComparison(
            comparison_id=comparison_id,
            scenario_ids=scenario_ids,
            best_scenario_id=best_scenario_id,
            comparison_summary={
                "scenarios": [{"id": s.id, "name": s.name} for s in scenarios],
                "metrics": metrics_list,
                "ranking": ranking,
                "scores": scores,
                "winner": {
                    "id": best_scenario_id,
                    "name": next((s.name for s in scenarios if s.id == best_scenario_id), None),
                    "score": scores.get(best_scenario_id, 0)
                },
                "runner_up": {
                    "id": runner_up_id,
                    "name": next((s.name for s in scenarios if s.id == runner_up_id), None),
                    "score": scores.get(runner_up_id, 0) if runner_up_id else None
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
                },
                "reason": f"Scenario {next((s.name for s in scenarios if s.id == best_scenario_id), 'Unknown')} is the overall winner with a score of {scores.get(best_scenario_id, 0):.2f}"
            },
            comparison_chart=comparison_chart
        )
        db.add(comparison)
        db.commit()
        db.refresh(comparison)
        
        return {
            "comparison_id": comparison_id,
            "scenarios": scenarios,
            "best_scenario_id": best_scenario_id,
            "comparison_summary": comparison.comparison_summary,
            "comparison_chart": comparison_chart,
            "created_at": comparison.created_at
        }
    
    @staticmethod
    def _generate_comparison_chart_enhanced(scenarios: List, metrics_list: List) -> Dict[str, Any]:
        """Enhanced comparison chart with all metrics."""
        labels = ["Demand Impact", "Inventory Impact", "Revenue Impact", "Stockout Risk"]
        chart_data = {
            "labels": labels,
            "baseline": [0, 0, 0, 0],
            "scenarios": {}
        }
        
        for item in metrics_list:
            metrics = item.get("metrics") or {}
            chart_data["scenarios"][item["name"]] = [
                metrics.get("demand_impact") or 0,
                metrics.get("inventory_impact") or 0,
                metrics.get("revenue_impact") or 0,
                metrics.get("stockout_risk") or 0
            ]
        
        return chart_data
    
    @staticmethod
    def get_comparison(db: Session, comparison_id: str) -> Dict[str, Any]:
        """Get a specific comparison."""
        comparison = db.query(ScenarioComparison).filter(
            ScenarioComparison.comparison_id == comparison_id
        ).first()
        
        if not comparison:
            return {"error": "Comparison not found"}
        
        scenarios = []
        for sid in comparison.scenario_ids:
            scenario = ScenarioService.get_scenario_by_id(db, sid)
            if scenario:
                scenarios.append(scenario)
        
        return {
            "comparison_id": comparison.comparison_id,
            "scenarios": scenarios,
            "best_scenario_id": comparison.best_scenario_id,
            "comparison_summary": comparison.comparison_summary,
            "comparison_chart": comparison.comparison_chart,
            "created_at": comparison.created_at
        }
    
    @staticmethod
    def get_comparison_history(db: Session, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get comparison history with pagination."""
        total = db.query(ScenarioComparison).count()
        comparisons = db.query(ScenarioComparison).order_by(
            desc(ScenarioComparison.created_at)
        ).offset(offset).limit(limit).all()
        
        items = [
            {
                "comparison_id": c.comparison_id,
                "scenario_count": len(c.scenario_ids),
                "best_scenario_id": c.best_scenario_id,
                "created_at": c.created_at,
                "summary": c.comparison_summary
            }
            for c in comparisons
        ]
        
        return {
            "total": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "pages": (total + limit - 1) // limit if limit > 0 and total > 0 else 1,
            "items": items
        }
    
    @staticmethod
    def delete_comparison(db: Session, comparison_id: str) -> bool:
        """Delete a comparison."""
        comparison = db.query(ScenarioComparison).filter(
            ScenarioComparison.comparison_id == comparison_id
        ).first()
        if not comparison:
            return False
        
        db.delete(comparison)
        db.commit()
        return True
    
    @staticmethod
    def update_comparison(db: Session, comparison_id: str, name: str) -> Dict[str, Any]:
        """Update comparison name (stored in summary)."""
        comparison = db.query(ScenarioComparison).filter(
            ScenarioComparison.comparison_id == comparison_id
        ).first()
        if not comparison:
            return {"error": "Comparison not found"}
        
        # Update name in summary
        if comparison.comparison_summary:
            comparison.comparison_summary["name"] = name
            db.commit()
        
        return ComparisonService.get_comparison(db, comparison_id)