# fastapi_app/schemas/recommendation_schema.py
"""
Recommendation Schemas - Updated for RecommendationResult model.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class RecommendationType(str, Enum):
    REORDER = "reorder"
    PROCUREMENT = "procurement"
    TRANSFER_STOCK = "transfer_stock"
    WAREHOUSE_OPTIMIZATION = "warehouse_optimization"
    SAFETY_STOCK = "safety_stock"
    SUPPLIER_DISCOUNT = "supplier_discount"
    BULK_PURCHASE = "bulk_purchase"
    OVERSTOCK = "overstock"
    CRITICAL_ALERT = "critical_alert"
    INVENTORY_OPTIMIZATION = "inventory_optimization"
    PROMOTION = "promotion"
    PRICE_REDUCTION = "price_reduction"
    DEMAND_SPIKE = "demand_spike"
    DEMAND_DROP = "demand_drop"
    SUPPLIER_RISK = "supplier_risk"
    SEASONAL_STOCK = "seasonal_stock"
    LOW_CONFIDENCE_ALERT = "low_confidence_alert"


class RecommendationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    IGNORED = "ignored"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


class RecommendationCategory(str, Enum):
    REORDER = "reorder"
    INVENTORY_OPTIMIZATION = "inventory_optimization"
    PROCUREMENT = "procurement"
    WAREHOUSE_OPTIMIZATION = "warehouse_optimization"
    OVERSTOCK_MANAGEMENT = "overstock_management"
    SUPPLIER_MANAGEMENT = "supplier_management"
    PRICING = "pricing"
    DEMAND_MANAGEMENT = "demand_management"
    RISK_MANAGEMENT = "risk_management"


class RecommendationJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# RECOMMENDATION SCHEMAS
# ============================================================================

class RecommendationResponse(BaseModel):
    id: int
    recommendation_job_id: Optional[int] = None
    forecast_job_id: Optional[str] = None
    
    sku: str
    title: str
    description: Optional[str] = None
    category: Optional[RecommendationCategory] = None
    recommendation_type: RecommendationType
    priority: RecommendationPriority
    status: RecommendationStatus
    
    business_reason: Optional[str] = None
    
    current_stock: Optional[float] = None
    recommended_quantity: float
    lead_time: Optional[str] = None
    inventory_days: Optional[float] = None
    holding_cost: Optional[float] = None
    stockout_probability: Optional[float] = None
    
    estimated_savings: Optional[float] = None
    estimated_revenue: Optional[float] = None
    estimated_cost: Optional[float] = None
    estimated_loss: Optional[float] = None
    expected_impact: Optional[str] = None
    
    ai_confidence: Optional[float] = None
    recommendation_score: Optional[float] = None
    risk_score: Optional[float] = None
    
    forecast_summary: Optional[Dict[str, Any]] = None
    forecast_accuracy: Optional[float] = None
    forecast_window: Optional[int] = None
    related_forecast: Optional[Dict[str, Any]] = None
    
    action_label: Optional[str] = None
    
    warehouse: Optional[str] = None
    region: Optional[str] = None
    
    forecast_value: Optional[float] = None
    current_demand: Optional[float] = None
    predicted_demand: Optional[float] = None
    
    supplier_name: Optional[str] = None
    supplier_discount_available: Optional[bool] = None
    discount_days: Optional[int] = None
    
    analysis: Optional[Dict[str, Any]] = None
    key_details: Optional[List[Dict[str, Any]]] = None
    
    executed_by: Optional[int] = None
    executed_at: Optional[datetime] = None
    ignored_by: Optional[int] = None
    ignored_at: Optional[datetime] = None
    ignored_reason: Optional[str] = None
    execution_notes: Optional[str] = None
    execution_status: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RecommendationDetailResponse(RecommendationResponse):
    history: List[Dict[str, Any]] = []


class RecommendationCreate(BaseModel):
    sku: str
    title: str
    description: Optional[str] = None
    category: Optional[RecommendationCategory] = None
    recommendation_type: RecommendationType
    priority: RecommendationPriority
    recommended_quantity: float
    current_stock: Optional[float] = None
    lead_time: Optional[str] = None
    estimated_savings: Optional[float] = None
    expected_impact: Optional[str] = None
    ai_confidence: Optional[float] = 80.0
    action_label: Optional[str] = None
    warehouse: Optional[str] = None
    region: Optional[str] = None
    forecast_value: Optional[float] = None
    supplier_name: Optional[str] = None
    key_details: Optional[List[Dict[str, Any]]] = None


class RecommendationUpdate(BaseModel):
    status: Optional[RecommendationStatus] = None
    priority: Optional[RecommendationPriority] = None
    recommended_quantity: Optional[float] = None
    estimated_savings: Optional[float] = None
    ai_confidence: Optional[float] = None
    action_label: Optional[str] = None
    description: Optional[str] = None


class RecommendationListResponse(BaseModel):
    page: int
    pages: int
    total: int
    limit: int
    items: List[RecommendationResponse]


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class RecommendationDashboardResponse(BaseModel):
    total: int
    pending: int
    executed: int
    ignored: int
    execution_rate: float
    
    executed_today: int
    today_savings: float
    total_savings: float
    
    average_confidence: float
    average_risk: float
    
    priority_breakdown: Dict[str, int]
    type_breakdown: Dict[str, int]
    category_breakdown: Dict[str, int]
    warehouse_breakdown: Dict[str, int]
    supplier_breakdown: Dict[str, int]
    
    top_skus: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    updated_at: str


class RecommendationTrendResponse(BaseModel):
    date: str
    generated: int
    savings: float
    executed: int
    executed_savings: float
    running_generated: int
    running_executed: int
    running_savings: float


# ============================================================================
# JOB SCHEMAS
# ============================================================================

class RecommendationJobResponse(BaseModel):
    id: int
    job_id: str
    forecast_job_id: str
    
    status: RecommendationJobStatus
    progress_percentage: float
    current_step: int
    current_step_name: Optional[str] = None
    
    failed_step: Optional[int] = None
    failed_step_name: Optional[str] = None
    current_step_message: Optional[str] = None
    
    total_recommendations: int
    saved_recommendations: int
    duplicates_removed: int
    
    forecast_summary: Optional[Dict[str, Any]] = None
    analysis_version: Optional[str] = None
    generator_version: Optional[str] = None
    recommendation_score: Optional[float] = None
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    elapsed_time: Optional[float] = None
    remaining_seconds: Optional[float] = None
    total_processing_time: Optional[float] = None
    job_duration: Optional[float] = None
    
    started_by: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    metrics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class RecommendationJobStatusResponse(BaseModel):
    status: str
    progress: float
    step: Optional[str] = None
    step_number: Optional[int] = None
    step_message: Optional[str] = None
    remaining_time: Optional[float] = None
    elapsed_time: Optional[float] = None
    estimated_completion: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    failed_step: Optional[int] = None
    failed_step_name: Optional[str] = None
    total_recommendations: int
    saved_recommendations: int
    duplicates_removed: int
    recommendation_score: Optional[float] = None


# ============================================================================
# ACTION SCHEMAS
# ============================================================================

class BulkActionResponse(BaseModel):
    success_count: int
    failed_count: int
    total: int
    total_savings: Optional[float] = None
    message: str


class ExecuteSummaryResponse(BaseModel):
    total_recommendations: int
    categories: Dict[str, int]
    estimated_savings: float
    critical_actions: int
    average_confidence: float
    by_priority: Dict[str, int]


# ============================================================================
# HISTORY SCHEMAS
# ============================================================================

class RecommendationHistoryResponse(BaseModel):
    id: int
    recommendation_id: int
    recommendation_job_id: Optional[int] = None
    
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    
    performed_by: Optional[int] = None
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    estimated_savings: Optional[float] = None
    ai_confidence: Optional[float] = None
    recommendation_score: Optional[float] = None
    forecast_value: Optional[float] = None
    
    performed_at: datetime
    
    class Config:
        from_attributes = True