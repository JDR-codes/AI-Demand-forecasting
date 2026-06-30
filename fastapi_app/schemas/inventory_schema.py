from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ============= Inventory SKU Schemas =============

class InventorySKUBase(BaseModel):
    sku: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit_cost: float
    holding_cost_per_year: float
    order_cost: float
    lead_time_days: int = 7
    min_order_quantity: int = 1


class InventorySKUCreate(InventorySKUBase):
    pass


class InventorySKUResponse(InventorySKUBase):
    id: int
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Warehouse Inventory Schemas =============

class WarehouseInventoryBase(BaseModel):
    sku: str
    warehouse: str
    region: str
    current_stock: float
    safety_stock: Optional[float] = None
    reorder_point: Optional[float] = None


class WarehouseInventoryCreate(WarehouseInventoryBase):
    pass


class WarehouseInventoryResponse(WarehouseInventoryBase):
    id: int
    economic_order_quantity: Optional[float] = None
    last_reorder_date: Optional[datetime] = None
    last_reorder_quantity: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Safety Stock Schemas =============

class SafetyStockDetail(BaseModel):
    sku: str
    warehouse: str
    region: str
    current_safety_stock: float
    recommended_safety_stock: float
    variance_percentage: float
    lead_time_days: int
    demand_std_dev: float
    service_level: float
    status: str  # below_target, optimal, above_target


class SafetyStockResponse(BaseModel):
    data: List[SafetyStockDetail]
    summary: dict  # avg_variance, total_understock_risk


# ============= Reorder Point Schemas =============

class ReorderPointDetail(BaseModel):
    sku: str
    warehouse: str
    current_stock: float
    reorder_point: float
    economic_order_quantity: float
    reorder_status: str  # URGENT_ORDER_NOW, PLANNED_REORDER, SAFE
    avg_daily_demand: float
    lead_time_days: int
    next_reorder_date: datetime
    forecasted_demand_next_30days: float
    days_until_stockout: Optional[int]


class ReorderPointResponse(BaseModel):
    data: List[ReorderPointDetail]
    total_urgent_reorders: int
    total_planned_reorders: int


# ============= Inventory Health Schemas =============

class InventoryHealthMetrics(BaseModel):
    stock_turnover_ratio: float
    fill_rate_percentage: float
    excess_stock_percentage: float
    stockout_risk_count: int


class InventoryHealthResponse(BaseModel):
    health_score: float
    status: str  # healthy, at_risk, critical
    total_skus: int
    at_risk_skus: int
    critical_skus: int
    metrics: InventoryHealthMetrics


# ============= Transfer Optimization Schemas =============

class InventoryTransferDetail(BaseModel):
    sku: str
    from_warehouse: str
    to_warehouse: str
    transfer_quantity: float
    reason: str
    priority: str
    transfer_cost: float
    cost_savings: float
    roi_percentage: float
    recommended_transfer_date: datetime
    expected_days_in_transit: int


class TransferOptimizationResponse(BaseModel):
    transfers: List[InventoryTransferDetail]
    total_transfers_recommended: int
    total_potential_savings: float


# ============= Excess Stock Schemas =============

class ExcessStockDetail(BaseModel):
    sku: str
    warehouse: str
    region: str
    current_stock: float
    forecasted_demand_30days: float
    days_inventory_on_hand: float
    excess_quantity: float
    carrying_cost_per_unit_yearly: float
    total_carrying_cost: float
    excess_level: str
    action_recommended: str
    estimated_liquidation_value: float
    potential_savings: float
    storage_risk_score: float


class ExcessStockResponse(BaseModel):
    excess_items: List[ExcessStockDetail]
    total_excess_quantity: float
    total_carrying_cost: float
    total_potential_savings: float
