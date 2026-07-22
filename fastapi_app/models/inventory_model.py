# fastapi_app/models/inventory_model.py
from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Index, Boolean, Text
from sqlalchemy.orm import relationship

from fastapi_app.db.session import Base


class InventorySKU(Base):
    __tablename__ = "inventory_skus"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    unit_cost = Column(Float, nullable=False)
    holding_cost_per_year = Column(Float, nullable=False)
    order_cost = Column(Float, nullable=False)
    lead_time_days = Column(Integer, default=7, nullable=False)
    min_order_quantity = Column(Integer, default=1, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ✅ Relationships
    warehouse_inventory = relationship(
        "WarehouseInventory",
        back_populates="inventory_sku",
        cascade="all, delete-orphan"
    )
    slow_moving_items = relationship(
        "SlowMovingInventory",
        back_populates="inventory_sku",
        cascade="all, delete-orphan"
    )
    excess_stock_items = relationship(
        "ExcessStock",
        back_populates="inventory_sku",
        cascade="all, delete-orphan"
    )
    safety_stock_calculations = relationship(
        "SafetyStockCalculation",
        back_populates="inventory_sku",
        cascade="all, delete-orphan"
    )

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
    
    # ✅ Inventory value - pre-calculated
    inventory_value = Column(Float, nullable=True)
    
    last_reorder_date = Column(DateTime, nullable=True)
    last_reorder_quantity = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ✅ Relationships
    inventory_sku = relationship(
        "InventorySKU",
        primaryjoin="WarehouseInventory.sku==InventorySKU.sku",
        foreign_keys=[sku],
        back_populates="warehouse_inventory",
        viewonly=True
    )
    slow_moving = relationship(
        "SlowMovingInventory",
        back_populates="warehouse_inventory",
        cascade="all, delete-orphan"
    )
    excess_stock = relationship(
        "ExcessStock",
        back_populates="warehouse_inventory",
        cascade="all, delete-orphan"
    )
    safety_stock_calcs = relationship(
        "SafetyStockCalculation",
        back_populates="warehouse_inventory",
        cascade="all, delete-orphan"
    )
    reorder_points = relationship(
        "ReorderPoint",
        back_populates="warehouse_inventory",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_warehouse_inventory_sku', 'sku'),
        Index('idx_warehouse_inventory_warehouse', 'warehouse'),
        Index('idx_warehouse_inventory_region', 'region'),
        Index('idx_warehouse_inventory_inventory_value', 'inventory_value'),
    )

    def __repr__(self):
        return f"<WarehouseInventory(sku={self.sku}, warehouse={self.warehouse})>"


class SafetyStockCalculation(Base):
    __tablename__ = "safety_stock_calculations"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    service_level = Column(Float, nullable=False)
    z_score = Column(Float, nullable=False)
    demand_std_dev = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    calculated_safety_stock = Column(Float, nullable=False)
    current_safety_stock = Column(Float, nullable=True)
    recommendation = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ✅ Relationships
    inventory_sku = relationship(
        "InventorySKU",
        primaryjoin="SafetyStockCalculation.sku==InventorySKU.sku",
        foreign_keys=[sku],
        back_populates="safety_stock_calculations",
        viewonly=True
    )
    warehouse_inventory = relationship(
        "WarehouseInventory",
        primaryjoin="and_(SafetyStockCalculation.sku==WarehouseInventory.sku, SafetyStockCalculation.warehouse==WarehouseInventory.warehouse)",
        foreign_keys=[sku, warehouse],
        back_populates="safety_stock_calcs",
        viewonly=True
    )

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
    reorder_status = Column(String(100), nullable=False)
    days_until_stockout = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ✅ Relationships
    warehouse_inventory = relationship(
        "WarehouseInventory",
        primaryjoin="and_(ReorderPoint.sku==WarehouseInventory.sku, ReorderPoint.warehouse==WarehouseInventory.warehouse)",
        foreign_keys=[sku, warehouse],
        back_populates="reorder_points",
        viewonly=True
    )

    def __repr__(self):
        return f"<ReorderPoint(sku={self.sku}, warehouse={self.warehouse})>"


class InventoryTransfer(Base):
    __tablename__ = "inventory_transfers"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    from_warehouse = Column(String(100), nullable=False)
    to_warehouse = Column(String(100), nullable=False)
    transfer_quantity = Column(Float, nullable=False)
    reason = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)
    transfer_cost = Column(Float, nullable=False)
    potential_cost_savings = Column(Float, nullable=False)
    roi_percentage = Column(Float, nullable=False)
    recommended_transfer_date = Column(DateTime, nullable=False)
    expected_days_in_transit = Column(Integer, default=2, nullable=False)
    
    # ✅ Transfer workflow
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, picking, packed, dispatched, in_transit, received, completed, cancelled
    approval_status = Column(String(50), nullable=True)
    approved_by = Column(String(100), nullable=True)
    completed_by = Column(String(100), nullable=True)
    expected_arrival = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    vehicle = Column(String(100), nullable=True)
    driver = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    transfer_number = Column(String(50), unique=True, nullable=True)
    
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
    excess_level = Column(String(50), nullable=False)
    carrying_cost_per_unit_yearly = Column(Float, nullable=False)
    total_carrying_cost = Column(Float, nullable=False)
    action_recommended = Column(String(100), nullable=False)
    estimated_liquidation_value = Column(Float, nullable=False)
    potential_savings = Column(Float, nullable=False)
    storage_risk_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ✅ Relationships
    inventory_sku = relationship(
        "InventorySKU",
        primaryjoin="ExcessStock.sku==InventorySKU.sku",
        foreign_keys=[sku],
        back_populates="excess_stock_items",
        viewonly=True
    )
    warehouse_inventory = relationship(
        "WarehouseInventory",
        primaryjoin="and_(ExcessStock.sku==WarehouseInventory.sku, ExcessStock.warehouse==WarehouseInventory.warehouse)",
        foreign_keys=[sku, warehouse],
        back_populates="excess_stock",
        viewonly=True
    )

    def __repr__(self):
        return f"<ExcessStock(sku={self.sku}, warehouse={self.warehouse})>"


class SlowMovingInventory(Base):
    __tablename__ = "slow_moving_inventory"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    region = Column(String(100), nullable=True)
    current_stock = Column(Float, nullable=False)
    avg_daily_sales = Column(Float, nullable=True)
    days_in_stock = Column(Float, nullable=True)
    turnover_ratio = Column(Float, nullable=True)
    last_sale_date = Column(DateTime, nullable=True)
    slow_moving_level = Column(String(50), nullable=True)
    action_recommended = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ✅ Relationships
    inventory_sku = relationship(
        "InventorySKU",
        primaryjoin="SlowMovingInventory.sku==InventorySKU.sku",
        foreign_keys=[sku],
        back_populates="slow_moving_items",
        viewonly=True
    )
    warehouse_inventory = relationship(
        "WarehouseInventory",
        primaryjoin="and_(SlowMovingInventory.sku==WarehouseInventory.sku, SlowMovingInventory.warehouse==WarehouseInventory.warehouse)",
        foreign_keys=[sku, warehouse],
        back_populates="slow_moving",
        viewonly=True
    )

    __table_args__ = (
        Index('idx_slow_moving_sku', 'sku'),
        Index('idx_slow_moving_warehouse', 'warehouse'),
        Index('idx_slow_moving_level', 'slow_moving_level'),
    )

    def __repr__(self):
        return f"<SlowMovingInventory(sku={self.sku}, warehouse={self.warehouse})>"


# ============================================================================
# INVENTORY HISTORY & MOVEMENTS
# ============================================================================

class InventoryHistory(Base):
    """Tracks all inventory changes."""
    __tablename__ = "inventory_history"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    old_stock = Column(Float, nullable=False)
    new_stock = Column(Float, nullable=False)
    change_amount = Column(Float, nullable=False)
    reason = Column(String(100), nullable=False)
    reference = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_inventory_history_sku', 'sku'),
        Index('idx_inventory_history_warehouse', 'warehouse'),
        Index('idx_inventory_history_created_at', 'created_at'),
        Index('idx_inventory_history_reason', 'reason'),
    )

    def __repr__(self):
        return f"<InventoryHistory(sku={self.sku}, warehouse={self.warehouse}, change={self.change_amount})>"


class InventoryMovement(Base):
    """Tracks inventory movements."""
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    warehouse = Column(String(100), index=True, nullable=False)
    movement_type = Column(String(50), nullable=False)  # purchase, sale, transfer, adjustment, return, damage
    quantity = Column(Float, nullable=False)
    reference_id = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_inventory_movements_sku', 'sku'),
        Index('idx_inventory_movements_warehouse', 'warehouse'),
        Index('idx_inventory_movements_type', 'movement_type'),
        Index('idx_inventory_movements_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<InventoryMovement(sku={self.sku}, type={self.movement_type}, qty={self.quantity})>"


# ============================================================================
# INVENTORY ALERTS
# ============================================================================

class InventoryAlert(Base):
    """Inventory alerts for monitoring."""
    __tablename__ = "inventory_alerts"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=True)
    warehouse = Column(String(100), index=True, nullable=True)
    alert_type = Column(String(50), nullable=False)  # critical_stock, reorder_needed, transfer_needed, excess_stock, slow_moving, warehouse_full, negative_inventory
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    is_read = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_inventory_alerts_sku', 'sku'),
        Index('idx_inventory_alerts_warehouse', 'warehouse'),
        Index('idx_inventory_alerts_type', 'alert_type'),
        Index('idx_inventory_alerts_severity', 'severity'),
        Index('idx_inventory_alerts_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<InventoryAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"