from math import floor
from typing import List, Any, Optional


def recommend_from_series(
    series: List[float],
    k: int = 3,
    sku: Optional[str] = None,
    region: Optional[str] = None,
    warehouse: Optional[str] = None,
) -> List[dict]:
    """Generate recommendations from a forecast or demand series."""
    if not series:
        return []

    mean = sum(series) / len(series)
    variance = sum((x - mean) ** 2 for x in series) / len(series)
    std = variance**0.5

    indexed = sorted(enumerate(series), key=lambda item: item[1], reverse=True)[:k]
    recommendations = []

    for idx, value in indexed:
        z_score = (value - mean) / std if std > 0 else 0.0
        if z_score >= 2.0:
            recommendation_type = "critical"
            priority = "critical"
            suggested_action = (
                "Immediate emergency action: increase stock levels now and verify supplier availability."
            )
        elif z_score >= 1.0:
            recommendation_type = "high"
            priority = "high"
            suggested_action = (
                "High priority reorder: prepare additional inventory to meet expected peak demand."
            )
        elif z_score >= 0.5:
            recommendation_type = "reorder"
            priority = "medium"
            suggested_action = (
                "Reorder recommended: top up inventory for the forecasted demand increase."
            )
        else:
            recommendation_type = "procurement"
            priority = "low"
            suggested_action = (
                "Procurement review: evaluate supplier orders for the upcoming period."
            )

        quantity = max(0.0, round((value - mean) * 1.2 + 1.0, 2)) if value > mean else round(value * 0.15 + 1.0, 2)
        forecast_period = idx + 1
        score = round((value - mean) / (abs(mean) + 1.0), 3)

        recommendations.append(
            {
                "sku": sku,
                "region": region,
                "warehouse": warehouse,
                "recommendation_type": recommendation_type,
                "priority": priority,
                "suggested_action": suggested_action,
                "quantity": quantity,
                "forecast_value": float(value),
                "forecast_period": forecast_period,
                "score": score,
            }
        )

    return recommendations
