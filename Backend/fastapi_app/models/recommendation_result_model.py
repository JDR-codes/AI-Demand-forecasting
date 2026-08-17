#fastapi_app/models/recommendation_result_model.py
"""
Recommendation Result Model - Stores generated recommendations.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON, Enum, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum


class RecommendationResultType(str, enum.Enum):
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


class RecommendationResultPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationResultStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    IGNORED = "ignored"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


class RecommendationResultCategory(str, enum.Enum):
    REORDER = "reorder"
    INVENTORY_OPTIMIZATION = "inventory_optimization"
    PROCUREMENT = "procurement"
    WAREHOUSE_OPTIMIZATION = "warehouse_optimization"
    OVERSTOCK_MANAGEMENT = "overstock_management"
    SUPPLIER_MANAGEMENT = "supplier_management"
    PRICING = "pricing"
    DEMAND_MANAGEMENT = "demand_management"
    RISK_MANAGEMENT = "risk_management"


class RecommendationResult(Base):
    """Individual recommendation generated from a forecast."""
    __tablename__ = "recommendation_results"
    
    id = Column(Integer, primary_key=True, index=True)
    forecast_job_id = Column(String(36), ForeignKey("forecast_jobs.job_id"), nullable=True, index=True)
    
    # Core fields
    sku = Column(String(100), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(RecommendationResultCategory), nullable=True)
    
    # Type, Priority, Status
    recommendation_type = Column(Enum(RecommendationResultType), nullable=False)
    priority = Column(Enum(RecommendationResultPriority), nullable=False)
    status = Column(Enum(RecommendationResultStatus), default=RecommendationResultStatus.PENDING, nullable=False)
    
    # Business reason
    business_reason = Column(Text, nullable=True)
    
    # Quantity and stock
    current_stock = Column(Float, nullable=True)
    recommended_quantity = Column(Float, nullable=False)
    lead_time = Column(String(50), nullable=True)
    inventory_days = Column(Float, nullable=True)
    holding_cost = Column(Float, nullable=True)
    stockout_probability = Column(Float, nullable=True)
    
    # Financial impact
    estimated_savings = Column(Float, nullable=True)
    estimated_revenue = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    estimated_loss = Column(Float, nullable=True)
    expected_impact = Column(String(255), nullable=True)
    
    # AI confidence and scores
    ai_confidence = Column(Float, default=80.0, nullable=True)
    recommendation_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    
    # Forecast link
    forecast_summary = Column(JSON, nullable=True)
    forecast_accuracy = Column(Float, nullable=True)
    forecast_window = Column(Integer, nullable=True)
    related_forecast = Column(JSON, nullable=True)
    
    # Action label
    action_label = Column(String(255), nullable=True)
    
    # Location
    warehouse = Column(String(100), index=True, nullable=True)
    region = Column(String(100), nullable=True)
    
    # Forecast and demand data
    forecast_value = Column(Float, nullable=True)
    current_demand = Column(Float, nullable=True)
    predicted_demand = Column(Float, nullable=True)
    
    # Supplier
    supplier_name = Column(String(255), nullable=True)
    supplier_discount_available = Column(Boolean, default=False)
    discount_days = Column(Integer, nullable=True)
    
    # Analysis details
    analysis = Column(JSON, nullable=True)
    
    # Additional details
    key_details = Column(JSON, nullable=True)
    
    # Execution tracking
    executed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    ignored_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    ignored_at = Column(DateTime, nullable=True)
    ignored_reason = Column(Text, nullable=True)
    execution_notes = Column(Text, nullable=True)
    execution_status = Column(String(50), default="pending")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    forecast_job = relationship("ForecastJob", foreign_keys=[forecast_job_id])
    executor = relationship("User", foreign_keys=[executed_by])
    ignorer = relationship("User", foreign_keys=[ignored_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_rec_result_sku', 'sku'),
        Index('idx_rec_result_status', 'status'),
        Index('idx_rec_result_priority', 'priority'),
        Index('idx_rec_result_type', 'recommendation_type'),
        Index('idx_rec_result_category', 'category'),
        Index('idx_rec_result_forecast_job', 'forecast_job_id'),
        Index('idx_rec_result_warehouse', 'warehouse'),
        Index('idx_rec_result_created_at', 'created_at'),
        Index('idx_rec_result_supplier_name', 'supplier_name'),
        Index('idx_rec_result_recommendation_score', 'recommendation_score'),
    )
    
    def __repr__(self):
        return f"<RecommendationResult(id={self.id}, sku={self.sku}, status={self.status})>"