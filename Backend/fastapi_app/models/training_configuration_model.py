# fastapi_app/models/training_configuration_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text, Index, JSON
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship


class TrainingConfiguration(Base):
    """Retraining configuration for models."""
    __tablename__ = "training_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    model_registry_id = Column(String(36), ForeignKey("model_registry.id"), nullable=True)
    
    # Extended configuration fields for Figma popup
    forecast_horizon = Column(Integer, default=30)
    seasonality = Column(Boolean, default=True)
    validation_split = Column(Float, default=0.2)
    
    # Training parameters
    epochs = Column(Integer, default=100)
    batch_size = Column(Integer, default=16)
    learning_rate = Column(Float, default=0.001)
    
    # Dataset configuration
    default_dataset = Column(String(255), nullable=True)
    default_region = Column(String(100), nullable=True)
    default_sku = Column(String(100), nullable=True)
    default_warehouse = Column(String(100), nullable=True)
    
    # Retraining schedule
    frequency = Column(String(50), default="daily")
    cron_expression = Column(String(100), nullable=True)
    accuracy_threshold = Column(Float, default=0.85)
    minimum_records = Column(Integer, default=100)
    
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    model_registry = relationship("ModelRegistry", back_populates="training_config")
    
    __table_args__ = (
        Index('idx_training_config_model', 'model_registry_id'),
        Index('idx_training_config_enabled', 'enabled'),
        Index('idx_training_config_frequency', 'frequency'),
    )
    
    def __repr__(self):
        return f"<TrainingConfiguration(id={self.id}, model={self.model_registry_id}, enabled={self.enabled})>"