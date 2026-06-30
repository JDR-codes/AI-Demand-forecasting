from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum

from fastapi_app.db.session import Base


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(str, enum.Enum):
    INVENTORY = "inventory"
    FORECAST = "forecast"
    REORDER = "reorder"
    EXCESS_STOCK = "excess_stock"
    TRANSFER = "transfer"
    SYSTEM = "system"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO, nullable=False)
    category = Column(Enum(AlertCategory), default=AlertCategory.SYSTEM, nullable=False)
    sku = Column(String(100), nullable=True)
    warehouse = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Alert(id={self.id}, severity={self.severity}, title={self.title!r})>"