# fastapi_app/models/forecast_configuration_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship


class ForecastConfiguration(Base):
    """Configuration settings specifically for forecast execution runs."""
    __tablename__ = "forecast_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    model_registry_id = Column(String(36), ForeignKey("model_registry.id"), nullable=True)
    
    # Forecast Run Parameters
    forecast_horizon = Column(Integer, default=30)
    seasonality = Column(Boolean, default=True)
    
    # Default selection constraints
    default_dataset = Column(String(255), default="Latest Processed Data")
    default_region = Column(String(100), nullable=True)
    default_sku = Column(String(100), nullable=True)
    default_warehouse = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    model_registry = relationship("ModelRegistry", back_populates="forecast_config")
    
    __table_args__ = (
        Index('idx_forecast_config_model', 'model_registry_id'),
    )
    
    def __repr__(self):
        return f"<ForecastConfiguration(id={self.id}, model={self.model_registry_id}, horizon={self.forecast_horizon})>"
