#fastapi_app/models/forecast_metric_history_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship


class ForecastMetricHistory(Base):
    """Historical forecast metrics for trend analysis."""
    __tablename__ = "forecast_metric_history"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(36), ForeignKey("model_registry.id"), nullable=True)
    model_type = Column(String(50), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    
    accuracy = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    
    job_id = Column(String(36), nullable=True)
    records = Column(Integer, default=0)
    
    # Relationships
    model_registry = relationship("ModelRegistry")
    
    __table_args__ = (
        Index('idx_metric_history_model', 'model_id'),
        Index('idx_metric_history_date', 'date'),
        Index('idx_metric_history_model_type', 'model_type'),
    )
    
    def __repr__(self):
        return f"<ForecastMetricHistory(id={self.id}, model={self.model_type}, date={self.date})>"