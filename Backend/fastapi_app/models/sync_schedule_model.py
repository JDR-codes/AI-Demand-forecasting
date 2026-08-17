# fastapi_app/models/sync_schedule_model.py
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Time,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from fastapi_app.db.session import Base


class SyncSchedule(Base):
    __tablename__ = "sync_schedules"

    id = Column(Integer, primary_key=True, index=True)

    # all / specific
    scope = Column(String(20), nullable=False)

    # custom / recurring
    schedule_type = Column(String(20), nullable=False)

    # daily / weekly / monthly
    frequency = Column(String(20), nullable=True)

    # fixed_time / interval
    run_method = Column(String(20), nullable=True)

    # IANA timezone
    timezone = Column(String(100), nullable=False, default="UTC")

    # Used when scope == specific
    data_source_ids = Column(JSON, nullable=True)

    # Custom Dates:
    # [
    #   {"date": "2026-08-15", "time": "09:00"},
    #   {"date": "2026-08-19", "time": "11:00"}
    # ]
    custom_runs = Column(JSON, nullable=True)

    # Daily/weekly fixed-time
    # ["09:00", "11:00"]
    run_times = Column(JSON, nullable=True)

    # Weekly
    # ["mon", "fri"]
    weekdays = Column(JSON, nullable=True)

    # Interval
    interval_value = Column(Integer, nullable=True)
    interval_unit = Column(String(20), nullable=True)

    window_start_time = Column(Time, nullable=True)
    window_end_time = Column(Time, nullable=True)

    # Daily/weekly range
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Monthly:
    # [
    #   {"day": 1, "time": "09:00"},
    #   {"day": 15, "time": "11:00"},
    #   {"day": "last", "time": "13:00"}
    # ]
    monthly_runs = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        Index("idx_sync_schedule_scope", "scope"),
        Index("idx_sync_schedule_type", "schedule_type"),
        Index("idx_sync_schedule_active", "is_active"),
    )

    def __repr__(self):
        return f"<SyncSchedule(id={self.id}, scope={self.scope}, type={self.schedule_type})>"