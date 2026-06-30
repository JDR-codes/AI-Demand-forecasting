from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ============= Recommendation Base Schemas =============

class RecommendationBase(BaseModel):
    sku: str
    recommendation_type: str  # critical, high, reorder, procurement
    priority: str  # critical, high, medium, low
    suggested_action: str
    quantity: float


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationUpdate(BaseModel):
    recommendation_type: Optional[str] = None
    priority: Optional[str] = None
    suggested_action: Optional[str] = None
    quantity: Optional[float] = None
    status: Optional[str] = None


class RecommendationResponse(RecommendationBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Bulk Action Schemas =============

class RecommendationBulkAction(BaseModel):
    recommendation_ids: List[int]
    action: str  # execute or ignore


class BulkActionResponse(BaseModel):
    success_count: int
    failed_count: int
    message: str


# ============= Forecast-based Recommendation Schemas =============

class RecommendationSeriesRequest(BaseModel):
    series: List[float]
    k: int = 3
    sku: Optional[str] = None
    region: Optional[str] = None
    warehouse: Optional[str] = None


class RecommendationPrediction(BaseModel):
    sku: Optional[str] = None
    region: Optional[str] = None
    warehouse: Optional[str] = None
    recommendation_type: str
    priority: str
    suggested_action: str
    quantity: float
    forecast_value: float
    forecast_period: int
    score: float


# ============= Filter Response Schemas =============

class CriticalRecommendationsResponse(BaseModel):
    total: int
    recommendations: List[RecommendationResponse]


class HighRecommendationsResponse(BaseModel):
    total: int
    recommendations: List[RecommendationResponse]


class ReorderRecommendationsResponse(BaseModel):
    total: int
    recommendations: List[RecommendationResponse]


class ProcurementRecommendationsResponse(BaseModel):
    total: int
    recommendations: List[RecommendationResponse]
