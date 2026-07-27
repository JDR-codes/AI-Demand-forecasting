# fastapi_app/models/scenario_model.py
"""
Scenario Models - Foundation for scenario simulation.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, ForeignKey, Text, Enum, Index
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
    """Scenario model - Contains filters and simulation inputs."""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    
    # Filters
    region = Column(String(100), nullable=True)
    warehouse = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)
    time_horizon = Column(Integer, default=30)
    
    # Simulation Inputs
    demand_surge = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    price_change = Column(Float, default=0.0)
    supply_delay = Column(Integer, default=0)
    seasonal_impact = Column(Float, default=0.0)
    
    # Forecast Model
    forecast_model = Column(String(50), default="arima")
    
    # Status
    status = Column(Enum(ScenarioStatus), default=ScenarioStatus.CREATED, nullable=False)
    progress = Column(Float, default=0.0)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Execution
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(50), nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
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
    """Scenario run - Tracks individual simulation executions."""
    __tablename__ = "scenario_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(String(36), unique=True, index=True, nullable=False)
    
    # Status and Progress
    status = Column(String(50), default="queued")
    progress = Column(Float, default=0.0)
    current_step = Column(String(100), nullable=True)
    step_number = Column(Integer, default=0)
    total_steps = Column(Integer, default=5)
    logs = Column(JSON, nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamp
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
    """Scenario result - Stores simulation results shown in UI."""
    __tablename__ = "scenario_results"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False)
    
    # Core Metrics
    demand_impact = Column(Float, nullable=True)
    inventory_impact = Column(Float, nullable=True)
    revenue_impact = Column(Float, nullable=True)
    stockout_risk = Column(Float, nullable=True)
    
    # Forecast Graph Data
    forecast_labels = Column(JSON, nullable=True)
    forecast_baseline = Column(JSON, nullable=True)
    forecast_simulation = Column(JSON, nullable=True)
    
    # Inventory Graph Data
    inventory_labels = Column(JSON, nullable=True)
    inventory_baseline = Column(JSON, nullable=True)
    inventory_simulation = Column(JSON, nullable=True)
    
    # Summary Cards
    summary_cards = Column(JSON, nullable=True)
    
    # Stockout Table
    stockout_skus = Column(JSON, nullable=True)
    stockout_count = Column(Integer, default=0)
    
    # Recommendations
    recommendation_ids = Column(JSON, nullable=True)
    
    # Additional metrics
    total_demand = Column(Float, nullable=True)
    total_inventory = Column(Float, nullable=True)
    total_revenue = Column(Float, nullable=True)
    
    # Timestamp
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
    """Scenario comparison - Stores comparison results."""
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