import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from fastapi_app.models.forecast_model import Forecast
from fastapi_app.models.inventory_model import (
    ExcessStock,
    InventoryTransfer,
    ReorderPoint,
    SafetyStockCalculation,
    WarehouseInventory,
)
from fastapi_app.models.recommendation_model import Recommendation
from fastapi_app.models.report_model import Report, ReportStatus
from fastapi_app.models.scenario_model import Scenario
from fastapi_app.schemas.report_schema import ReportGenerateRequest

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

VALID_TYPES = {
    "forecast_summary",
    "inventory_health",
    "recommendation_summary",
    "scenario_comparison",
    "full_system",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_dict(obj) -> Dict[str, Any]:
    """Convert a SQLAlchemy model instance to a plain serialisable dict."""
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        d[col.name] = val
    return d


# ─────────────────────────────────────────────────────────────────────────────
# Per-type data generators
# ─────────────────────────────────────────────────────────────────────────────

def _generate_forecast_summary(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    q = db.query(Forecast)
    if params.get("sku"):
        q = q.filter(Forecast.sku == params["sku"])
    if params.get("warehouse"):
        q = q.filter(Forecast.warehouse == params["warehouse"])
    if params.get("region"):
        q = q.filter(Forecast.region == params["region"])
    limit = int(params.get("limit", 100))
    forecasts = q.order_by(Forecast.created_at.desc()).limit(limit).all()

    rows = [_row_to_dict(f) for f in forecasts]
    total = len(rows)
    avg_demand = (sum(r["predicted_demand"] for r in rows) / total) if total else 0
    confidence_values = [r["confidence_score"] for r in rows if r.get("confidence_score") is not None]
    avg_confidence = (sum(confidence_values) / len(confidence_values)) if confidence_values else 0
    models_used = list({r["model_used"] for r in rows})

    return {
        "report_type": "forecast_summary",
        "generated_at": datetime.utcnow().isoformat(),
        "filters": params,
        "total_records": total,
        "statistics": {
            "average_predicted_demand": round(avg_demand, 2),
            "average_confidence_score": round(avg_confidence, 4),
            "models_used": models_used,
        },
        "forecasts": rows,
    }


def _generate_inventory_health(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    sku_filter = params.get("sku")
    wh_filter = params.get("warehouse")
    limit = int(params.get("limit", 100))

    wh_q = db.query(WarehouseInventory)
    if sku_filter:
        wh_q = wh_q.filter(WarehouseInventory.sku == sku_filter)
    if wh_filter:
        wh_q = wh_q.filter(WarehouseInventory.warehouse == wh_filter)
    wh_rows = [_row_to_dict(r) for r in wh_q.limit(limit).all()]

    reorder_q = db.query(ReorderPoint)
    if sku_filter:
        reorder_q = reorder_q.filter(ReorderPoint.sku == sku_filter)
    reorder_rows = [_row_to_dict(r) for r in reorder_q.limit(limit).all()]
    urgent_reorders = [r for r in reorder_rows if r.get("reorder_status") == "URGENT_ORDER_NOW"]

    excess_q = db.query(ExcessStock)
    if sku_filter:
        excess_q = excess_q.filter(ExcessStock.sku == sku_filter)
    excess_rows = [_row_to_dict(r) for r in excess_q.limit(limit).all()]
    total_carrying_cost = sum(r.get("total_carrying_cost", 0) or 0 for r in excess_rows)

    transfers_q = db.query(InventoryTransfer)
    if sku_filter:
        transfers_q = transfers_q.filter(InventoryTransfer.sku == sku_filter)
    transfer_rows = [_row_to_dict(r) for r in transfers_q.limit(limit).all()]

    safety_q = db.query(SafetyStockCalculation)
    if sku_filter:
        safety_q = safety_q.filter(SafetyStockCalculation.sku == sku_filter)
    safety_rows = [_row_to_dict(r) for r in safety_q.limit(limit).all()]

    return {
        "report_type": "inventory_health",
        "generated_at": datetime.utcnow().isoformat(),
        "filters": params,
        "summary": {
            "total_warehouse_records": len(wh_rows),
            "urgent_reorder_count": len(urgent_reorders),
            "excess_stock_items": len(excess_rows),
            "total_carrying_cost": round(total_carrying_cost, 2),
            "pending_transfers": len([t for t in transfer_rows if t.get("status") == "recommended"]),
        },
        "warehouse_inventory": wh_rows,
        "reorder_points": reorder_rows,
        "excess_stock": excess_rows,
        "inventory_transfers": transfer_rows,
        "safety_stock_calculations": safety_rows,
    }


def _generate_recommendation_summary(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    q = db.query(Recommendation)
    if params.get("sku"):
        q = q.filter(Recommendation.sku == params["sku"])
    if params.get("status"):
        q = q.filter(Recommendation.status == params["status"])
    if params.get("priority"):
        q = q.filter(Recommendation.priority == params["priority"])
    limit = int(params.get("limit", 100))
    recs = [_row_to_dict(r) for r in q.order_by(Recommendation.created_at.desc()).limit(limit).all()]

    by_priority: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    for r in recs:
        p = r.get("priority", "unknown")
        t = r.get("recommendation_type", "unknown")
        by_priority[p] = by_priority.get(p, 0) + 1
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "report_type": "recommendation_summary",
        "generated_at": datetime.utcnow().isoformat(),
        "filters": params,
        "total_records": len(recs),
        "breakdown_by_priority": by_priority,
        "breakdown_by_type": by_type,
        "recommendations": recs,
    }


def _generate_scenario_comparison(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    q = db.query(Scenario)
    if params.get("status"):
        q = q.filter(Scenario.status == params["status"])
    limit = int(params.get("limit", 50))
    scenarios = [_row_to_dict(s) for s in q.order_by(Scenario.created_at.desc()).limit(limit).all()]

    completed = [s for s in scenarios if s.get("status") == "completed"]
    failed = [s for s in scenarios if s.get("last_run_status") == "failed"]

    # Extract forecast results from last_run_output for comparison
    comparison = []
    for s in scenarios:
        output = s.get("last_run_output") or {}
        forecast_results = output.get("forecast_results", {})
        comparison.append({
            "id": s["id"],
            "name": s.get("name"),
            "status": s.get("status"),
            "model_type": (s.get("parameters") or {}).get("model_type", "unknown"),
            "forecast_steps": (s.get("parameters") or {}).get("forecast_steps"),
            "last_run_status": s.get("last_run_status"),
            "last_run_at": s.get("last_run_at"),
            "forecast_type": forecast_results.get("type"),
            "forecast_count": len(forecast_results.get("forecast", [])) if isinstance(forecast_results.get("forecast"), list) else None,
            "recommendations_count": len(output.get("recommendations", [])),
        })

    return {
        "report_type": "scenario_comparison",
        "generated_at": datetime.utcnow().isoformat(),
        "filters": params,
        "total_scenarios": len(scenarios),
        "completed_count": len(completed),
        "failed_count": len(failed),
        "comparison_table": comparison,
        "scenarios": scenarios,
    }


def _generate_full_system(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    forecast_data = _generate_forecast_summary(db, params)
    inventory_data = _generate_inventory_health(db, params)
    rec_data = _generate_recommendation_summary(db, params)
    scenario_data = _generate_scenario_comparison(db, params)

    return {
        "report_type": "full_system",
        "generated_at": datetime.utcnow().isoformat(),
        "filters": params,
        "executive_summary": {
            "forecast": {
                "total_records": forecast_data["total_records"],
                "statistics": forecast_data["statistics"],
            },
            "inventory": inventory_data["summary"],
            "recommendations": {
                "total_records": rec_data["total_records"],
                "breakdown_by_priority": rec_data["breakdown_by_priority"],
                "breakdown_by_type": rec_data["breakdown_by_type"],
            },
            "scenarios": {
                "total": scenario_data["total_scenarios"],
                "completed": scenario_data["completed_count"],
                "failed": scenario_data["failed_count"],
            },
        },
        "detail": {
            "forecast_summary": forecast_data,
            "inventory_health": inventory_data,
            "recommendation_summary": rec_data,
            "scenario_comparison": scenario_data,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# CSV export helper
# ─────────────────────────────────────────────────────────────────────────────

def _flatten_for_csv(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find the first non-empty list of dicts in data and use it as CSV rows."""
    for val in data.values():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            return val
    # Fallback: top-level scalars as a single row
    return [{k: v for k, v in data.items() if not isinstance(v, (dict, list))}]


def data_to_csv(data: Dict[str, Any]) -> str:
    rows = _flatten_for_csv(data)
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Main service class
# ─────────────────────────────────────────────────────────────────────────────

class ReportService:

    @staticmethod
    def list_reports(db: Session) -> List[Report]:
        return db.query(Report).order_by(Report.created_at.desc()).all()

    @staticmethod
    def get_report(db: Session, report_id: int) -> Optional[Report]:
        return db.query(Report).filter(Report.id == report_id).first()

    @staticmethod
    def generate_report(
        db: Session,
        payload: ReportGenerateRequest,
        user_id: int,
    ) -> Report:
        if payload.report_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid report_type '{payload.report_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_TYPES))}"
            )

        fmt = (payload.format or "json").lower()
        if fmt not in ("json", "csv"):
            fmt = "json"

        title = (
            payload.title
            or f"{payload.report_type.replace('_', ' ').title()} — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
        params = payload.parameters or {}

        # Persist a PENDING record immediately so caller gets an id
        report = Report(
            title=title,
            report_type=payload.report_type,
            status=ReportStatus.PENDING,
            format=fmt,
            parameters=params,
            generated_by=user_id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Mark as generating
        report.status = ReportStatus.GENERATING
        db.add(report)
        db.commit()

        # Run generation
        try:
            generators = {
                "forecast_summary": _generate_forecast_summary,
                "inventory_health": _generate_inventory_health,
                "recommendation_summary": _generate_recommendation_summary,
                "scenario_comparison": _generate_scenario_comparison,
                "full_system": _generate_full_system,
            }
            raw_data = generators[payload.report_type](db, params)

            if fmt == "csv":
                csv_str = data_to_csv(raw_data)
                report.data = {
                    "csv_content": csv_str,
                    "meta": {k: v for k, v in raw_data.items() if not isinstance(v, (list, dict))},
                }
            else:
                report.data = raw_data

            total = raw_data.get("total_records") or raw_data.get("total_scenarios") or "N/A"
            report.summary = (
                f"Report '{title}' generated successfully. "
                f"Type: {payload.report_type}. Records: {total}."
            )
            report.status = ReportStatus.COMPLETED
            report.generated_at = datetime.utcnow()

        except Exception as exc:
            report.status = ReportStatus.FAILED
            report.error_message = str(exc)
            report.generated_at = datetime.utcnow()

        report.updated_at = datetime.utcnow()
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_download_content(report: Report):
        """Return (content, media_type, filename) for the download endpoint."""
        if report.status != ReportStatus.COMPLETED:
            raise ValueError("Report is not ready for download.")

        if report.format == "csv":
            csv_data = (report.data or {}).get("csv_content", "")
            filename = f"report_{report.id}_{report.report_type}.csv"
            return csv_data, "text/csv", filename
        else:
            content = json.dumps(report.data, indent=2, default=str)
            filename = f"report_{report.id}_{report.report_type}.json"
            return content, "application/json", filename
