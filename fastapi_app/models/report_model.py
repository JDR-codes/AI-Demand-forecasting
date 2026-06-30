from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text

from fastapi_app.db.session import Base


class ReportType(str, enum.Enum):
    FORECAST_SUMMARY = "forecast_summary"
    INVENTORY_HEALTH = "inventory_health"
    RECOMMENDATION_SUMMARY = "recommendation_summary"
    SCENARIO_COMPARISON = "scenario_comparison"
    FULL_SYSTEM = "full_system"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportFormat(str, enum.Enum):
    JSON = "json"
    CSV = "csv"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False)
    status = Column(String(50), default=ReportStatus.PENDING, nullable=False)
    format = Column(String(20), default=ReportFormat.JSON, nullable=False)
    parameters = Column(JSON, nullable=True)       # filters used to generate
    data = Column(JSON, nullable=True)             # actual report payload
    summary = Column(Text, nullable=True)          # human-readable summary
    generated_by = Column(Integer, nullable=True)  # user id
    generated_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Report(id={self.id}, type={self.report_type}, status={self.status})>"
