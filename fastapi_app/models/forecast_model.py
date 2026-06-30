from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum

from fastapi_app.db.session import Base


class ForecastStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(255), index=True, nullable=True)
    sku = Column(String(100), index=True, nullable=False)
    region = Column(String(100), nullable=False)
    warehouse = Column(String(100), nullable=False)
    model_used = Column(String(100), nullable=False)
    horizon = Column(Integer, nullable=False)  # Number of periods to forecast
    predicted_demand = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=True)  # 0-1 score
    forecast_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Forecast(id={self.id}, sku={self.sku}, model_used={self.model_used})>"
