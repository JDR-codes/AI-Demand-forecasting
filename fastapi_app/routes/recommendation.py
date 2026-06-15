from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from fastapi_app.services.recommendation.recommendation_service import recommend_from_series


class RecRequest(BaseModel):
    series: List[float]
    k: int = 3


router = APIRouter(prefix="/api/recommendation")


@router.post("/predict")
def recommend(req: RecRequest):
    if not req.series:
        raise HTTPException(status_code=400, detail="empty series")
    recs = recommend_from_series(req.series, k=req.k)
    return {"recommendations": recs}
