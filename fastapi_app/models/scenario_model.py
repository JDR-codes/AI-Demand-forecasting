# fastapi_app/models/scenario_model.py
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, ForeignKey, Text, Enum, Index, Boolean
from sqlalchemy.orm import relationship
import enum

from fastapi_app.db.session import Base


class ScenarioStatus(str, enum.Enum):
    DRAFT = "draft"
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    
    # Filtering and categorization
    time_horizon = Column(Integer, default=30)
    region = Column(String(100), nullable=True)
    warehouse = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)
    
    # Scenario adjustment parameters
    demand_surge = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    price_change = Column(Float, default=0.0)
    supply_delay = Column(Integer, default=0)
    seasonal_impact = Column(Float, default=0.0)
    
    # Status and tracking
    status = Column(Enum(ScenarioStatus), default=ScenarioStatus.CREATED, nullable=False)
    progress = Column(Float, default=0.0)
    
    # Forecast model
    forecast_model = Column(String(50), default="arima")
    
    # Legacy fields
    parameters = Column(JSON, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(50), nullable=True)
    last_run_output = Column(JSON, nullable=True)
    
    # ✅ Audit Trail
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    executed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    exported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    exported_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    executor = relationship("User", foreign_keys=[executed_by])
    deleter = relationship("User", foreign_keys=[deleted_by])
    exporter = relationship("User", foreign_keys=[exported_by])
    scenario_runs = relationship("ScenarioRun", back_populates="scenario", cascade="all, delete-orphan")
    scenario_results = relationship("ScenarioResult", back_populates="scenario", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_scenario_status', 'status'),
        Index('idx_scenario_created_by', 'created_by'),
        Index('idx_scenario_created_at', 'created_at'),
        Index('idx_scenario_region', 'region'),
        Index('idx_scenario_warehouse', 'warehouse'),
        Index('idx_scenario_sku', 'sku'),
        Index('idx_scenario_category', 'category'),
        Index('idx_scenario_forecast_model', 'forecast_model'),
        Index('idx_scenario_last_run_status', 'last_run_status'),
    )

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, name={self.name}, status={self.status})>"


class ScenarioRun(Base):
    """Tracks individual simulation runs."""
    __tablename__ = "scenario_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(String(36), unique=True, index=True, nullable=False)
    
    status = Column(String(50), default="queued")
    progress = Column(Float, default=0.0)
    current_step = Column(String(100), nullable=True)
    step_number = Column(Integer, default=0)
    total_steps = Column(Integer, default=8)
    logs = Column(JSON, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scenario = relationship("Scenario", back_populates="scenario_runs")
    user = relationship("User", foreign_keys=[user_id])
    scenario_results = relationship("ScenarioResult", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_scenario_run_scenario', 'scenario_id'),
        Index('idx_scenario_run_status', 'status'),
        Index('idx_scenario_run_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScenarioRun(id={self.id}, run_id={self.run_id}, status={self.status})>"


class ScenarioResult(Base):
    """Stores simulation results for a scenario run."""
    __tablename__ = "scenario_results"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False)
    
    # Core metrics
    demand_impact = Column(Float, nullable=True)
    inventory_impact = Column(Float, nullable=True)
    revenue_impact = Column(Float, nullable=True)
    stockout_risk = Column(Float, nullable=True)
    
    # Detailed data
    stockout_skus = Column(JSON, nullable=True)
    forecast_json = Column(JSON, nullable=True)
    inventory_json = Column(JSON, nullable=True)
    summary_json = Column(JSON, nullable=True)
    
    # Chart data
    forecast_labels = Column(JSON, nullable=True)
    forecast_baseline = Column(JSON, nullable=True)
    forecast_simulation = Column(JSON, nullable=True)
    forecast_difference = Column(JSON, nullable=True)
    
    inventory_labels = Column(JSON, nullable=True)
    inventory_baseline = Column(JSON, nullable=True)
    inventory_simulation = Column(JSON, nullable=True)
    inventory_difference = Column(JSON, nullable=True)
    
    # All SKU data
    all_skus = Column(JSON, nullable=True)
    
    # Recommendation IDs
    recommendation_ids = Column(JSON, nullable=True)
    
    # Summary cards
    summary_cards = Column(JSON, nullable=True)
    
    # Additional metrics
    total_demand = Column(Float, nullable=True)
    total_inventory = Column(Float, nullable=True)
    total_revenue = Column(Float, nullable=True)
    stockout_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scenario = relationship("Scenario", back_populates="scenario_results")
    run = relationship("ScenarioRun", back_populates="scenario_results")
    
    __table_args__ = (
        Index('idx_scenario_result_scenario', 'scenario_id'),
        Index('idx_scenario_result_run', 'run_id'),
        Index('idx_scenario_result_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScenarioResult(id={self.id}, scenario_id={self.scenario_id})>"


class ScenarioComparison(Base):
    """Stores comparison results between scenarios."""
    __tablename__ = "scenario_comparisons"
    
    id = Column(Integer, primary_key=True, index=True)
    comparison_id = Column(String(36), unique=True, index=True, nullable=False)
    
    scenario_ids = Column(JSON, nullable=False)
    best_scenario_id = Column(Integer, nullable=True)
    comparison_summary = Column(JSON, nullable=True)
    comparison_chart = Column(JSON, nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    best_scenario = relationship("Scenario", foreign_keys=[best_scenario_id])
    
    __table_args__ = (
        Index('idx_scenario_comparison_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScenarioComparison(id={self.id}, comparison_id={self.comparison_id})>"