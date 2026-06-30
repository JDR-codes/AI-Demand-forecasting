from fastapi import APIRouter, HTTPException
from typing import List, Optional

from fastapi_app.schemas.recommendation_schema import (
    RecommendationSeriesRequest,
    RecommendationPrediction,
)
from fastapi_app.services.recommendation.recommendation_service import recommend_from_series


router = APIRouter(prefix="/api/recommendation")


@router.post("/predict", response_model=List[RecommendationPrediction])
def recommend(req: RecommendationSeriesRequest):
    if not req.series:
        raise HTTPException(status_code=400, detail="empty series")

    recommendations = recommend_from_series(
        req.series,
        k=req.k,
        sku=req.sku,
        region=req.region,
        warehouse=req.warehouse,
    )
    return recommendations
