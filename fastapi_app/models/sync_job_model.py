# fastapi_app/models/sync_job_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Enum, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum


class SyncJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncJobStep(str, enum.Enum):
    CONNECTING = "connecting"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    SAVING = "saving"
    COMPLETED = "completed"


class SyncJob(Base):
    """Sync job for data sources - tracks progress and status."""
    __tablename__ = "sync_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    
    status = Column(Enum(SyncJobStatus), default=SyncJobStatus.QUEUED)
    current_step = Column(Enum(SyncJobStep), default=SyncJobStep.CONNECTING)
    progress_percentage = Column(Float, default=0.0)
    
    rows_processed = Column(Integer, default=0)
    rows_total = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    eta_seconds = Column(Float, nullable=True)
    
    triggered_by = Column(String(50), default="manual")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - ✅ FIXED: Use correct model name
    datasource = relationship("DataSource", back_populates="sync_jobs")
    sync_job_steps = relationship(
        "SyncJobStepDetail",  # ✅ Fixed: Use SyncJobStepDetail, not SyncJobStep
        back_populates="sync_job",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_sync_jobs_datasource', 'datasource_id'),
        Index('idx_sync_jobs_status', 'status'),
        Index('idx_sync_jobs_created_at', 'created_at'),
        Index('idx_sync_jobs_triggered_by', 'triggered_by'),
    )
    
    def __repr__(self):
        return f"<SyncJob(id={self.id}, job_id={self.job_id}, status={self.status})>"


class SyncJobStepDetail(Base):
    """Individual steps within a sync job."""
    __tablename__ = "sync_job_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_job_id = Column(Integer, ForeignKey("sync_jobs.id", ondelete="CASCADE"), index=True)
    
    step_name = Column(Enum(SyncJobStep), nullable=False)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    
    # Relationships
    sync_job = relationship("SyncJob", back_populates="sync_job_steps")
    
    __table_args__ = (
        Index('idx_sync_job_steps_job', 'sync_job_id'),
        Index('idx_sync_job_steps_status', 'status'),
    )
    
    def __repr__(self):
        return f"<SyncJobStepDetail(id={self.id}, step_name={self.step_name}, status={self.status})>"