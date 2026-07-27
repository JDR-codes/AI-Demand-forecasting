# fastapi_app/schemas/inventory_schema.py
"""
Inventory Schemas - Simplified for Dashboard only.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ============= DASHBOARD RESPONSE =============

class HealthCardsResponse(BaseModel):
    overall_health: float
    status: str  # healthy, at_risk, critical
    inventory_turnover: float
    fill_rate: float
    stockout_risk_percentage: float
    total_skus: int
    at_risk_skus: int
    critical_skus: int


class ReorderPointResponse(BaseModel):
    product_name: str
    sku: str
    current: float
    reorder_point: float
    safety_stock: Optional[float] = None
    days_to_stockout: Optional[int] = None
    status: str  # Critical, Low, Optimal


class ExcessInventoryResponse(BaseModel):
    sku: str
    warehouse: str
    current_stock: float
    excess_quantity: float
    days_inventory_on_hand: float
    excess_level: str  # critical, high, medium, low


class SlowMovingResponse(BaseModel):
    product_name: str
    sku: str
    turnover_ratio: float
    current_stock: float
    days_in_stock: float
    slow_moving_level: str  # critical, high, medium, low


class WarehouseDistributionResponse(BaseModel):
    warehouse: str
    total_units: float
    percentage: float


class InventoryValueDistributionResponse(BaseModel):
    warehouse: str
    inventory_value: float
    percentage: float


class WarehouseSummaryResponse(BaseModel):
    warehouse: str
    region: str
    total_units: float
    inventory_value: float
    item_types: int


class TransferRecommendationResponse(BaseModel):
    product_name: str
    sku: str
    quantity: float
    from_warehouse: str
    to_warehouse: str
    priority: str  # high, medium, low
    status: str  # pending, approved, completed


class InventoryDashboardResponse(BaseModel):
    health_cards: HealthCardsResponse
    reorder_points: List[ReorderPointResponse]
    excess_inventory: List[ExcessInventoryResponse]
    slow_moving_items: List[SlowMovingResponse]
    warehouse_distribution: List[WarehouseDistributionResponse]
    inventory_value_distribution: List[InventoryValueDistributionResponse]
    warehouse_summary: List[WarehouseSummaryResponse]
    transfer_recommendations: List[TransferRecommendationResponse]
    timestamp: str


# ============= ALERT RESPONSE =============

class AlertResponse(BaseModel):
    id: int
    sku: Optional[str] = None
    warehouse: Optional[str] = None
    message: str
    severity: str  # critical, high, medium, low
    is_read: bool
    created_at: datetime


# ============= UPDATE STOCK =============

class UpdateStockRequest(BaseModel):
    sku: str
    warehouse: str
    new_quantity: float
    reason: str


class UpdateStockResponse(BaseModel):
    success: bool
    sku: str
    warehouse: str
    old_quantity: float
    new_quantity: float
    change: float
    inventory_value: Optional[float] = None
    message: str