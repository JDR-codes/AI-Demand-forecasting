from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey

from fastapi_app.db.session import Base


class InventorySKU(Base):
    __tablename__ = "inventory_skus"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    unit_cost = Column(Float, nullable=False)
    holding_cost_per_year = Column(Float, nullable=False)  # Annual carrying cost per unit
    order_cost = Column(Float, nullable=False)  # Cost to place an order
    lead_time_days = Column(Integer, default=7, nullable=False)
    min_order_quantity = Column(Integer, default=1, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<InventorySKU(id={self.id}, sku={self.sku})>"


class WarehouseInventory(Base):
    __tablename__ = "warehouse_inventory"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    region = Column(String(100), nullable=False)
    current_stock = Column(Float, nullable=False)
    safety_stock = Column(Float, nullable=True)
    reorder_point = Column(Float, nullable=True)
    economic_order_quantity = Column(Float, nullable=True)
    last_reorder_date = Column(DateTime, nullable=True)
    last_reorder_quantity = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<WarehouseInventory(sku={self.sku}, warehouse={self.warehouse})>"


class SafetyStockCalculation(Base):
    __tablename__ = "safety_stock_calculations"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    service_level = Column(Float, nullable=False)  # 95, 99, etc.
    z_score = Column(Float, nullable=False)
    demand_std_dev = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    calculated_safety_stock = Column(Float, nullable=False)
    current_safety_stock = Column(Float, nullable=True)
    recommendation = Column(String(100), nullable=True)  # "increase", "decrease", "optimal"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SafetyStockCalculation(sku={self.sku}, warehouse={self.warehouse})>"


class ReorderPoint(Base):
    __tablename__ = "reorder_points"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    avg_daily_demand = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    safety_stock = Column(Float, nullable=False)
    reorder_point_value = Column(Float, nullable=False)
    economic_order_quantity = Column(Float, nullable=False)
    current_stock = Column(Float, nullable=False)
    reorder_status = Column(String(100), nullable=False)  # URGENT_ORDER_NOW, PLANNED_REORDER, SAFE
    days_until_stockout = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ReorderPoint(sku={self.sku}, warehouse={self.warehouse})>"


class InventoryTransfer(Base):
    __tablename__ = "inventory_transfers"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    from_warehouse = Column(String(100), nullable=False)
    to_warehouse = Column(String(100), nullable=False)
    transfer_quantity = Column(Float, nullable=False)
    reason = Column(String(100), nullable=False)  # excess_to_shortage, rebalancing, etc.
    priority = Column(String(50), nullable=False)  # high, medium, low
    transfer_cost = Column(Float, nullable=False)
    potential_cost_savings = Column(Float, nullable=False)
    roi_percentage = Column(Float, nullable=False)
    recommended_transfer_date = Column(DateTime, nullable=False)
    expected_days_in_transit = Column(Integer, default=2, nullable=False)
    status = Column(String(50), default="recommended", nullable=False)  # recommended, in_transit, completed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<InventoryTransfer(sku={self.sku}, from={self.from_warehouse}, to={self.to_warehouse})>"


class ExcessStock(Base):
    __tablename__ = "excess_stock"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    region = Column(String(100), nullable=False)
    current_stock = Column(Float, nullable=False)
    forecasted_demand_30days = Column(Float, nullable=False)
    excess_quantity = Column(Float, nullable=False)
    days_inventory_on_hand = Column(Float, nullable=False)
    excess_level = Column(String(50), nullable=False)  # critical, high, medium, low
    carrying_cost_per_unit_yearly = Column(Float, nullable=False)
    total_carrying_cost = Column(Float, nullable=False)
    action_recommended = Column(String(100), nullable=False)  # aggressive_discount, transfer, clearance, donation
    estimated_liquidation_value = Column(Float, nullable=False)
    potential_savings = Column(Float, nullable=False)
    storage_risk_score = Column(Float, nullable=False)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ExcessStock(sku={self.sku}, warehouse={self.warehouse})>"
