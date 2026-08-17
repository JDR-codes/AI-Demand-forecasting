#fastapi_app/models/scheduler_history_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Index
from fastapi_app.db.session import Base


class SchedulerHistory(Base):
    """History of scheduler job executions."""
    __tablename__ = "scheduler_history"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), nullable=False)
    job_type = Column(String(50), nullable=False)  # sync, training
    entity_id = Column(String(36), nullable=True)
    
    status = Column(String(50), default="running")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_scheduler_history_job', 'job_id'),
        Index('idx_scheduler_history_type', 'job_type'),
        Index('idx_scheduler_history_started', 'started_at'),
        Index('idx_scheduler_history_status', 'status'),
    )
    
    def __repr__(self):
        return f"<SchedulerHistory(id={self.id}, job={self.job_id}, status={self.status})>"