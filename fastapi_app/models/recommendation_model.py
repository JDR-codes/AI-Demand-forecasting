from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum

from fastapi_app.db.session import Base


class RecommendationType(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    REORDER = "reorder"
    PROCUREMENT = "procurement"


class RecommendationPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    IGNORED = "ignored"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True, nullable=False)
    recommendation_type = Column(String(100), nullable=False)  # critical, high, reorder, procurement
    priority = Column(String(50), nullable=False)  # critical, high, medium, low
    suggested_action = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    status = Column(String(50), default=RecommendationStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Recommendation(id={self.id}, sku={self.sku}, type={self.recommendation_type})>"
