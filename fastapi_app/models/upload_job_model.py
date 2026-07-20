# fastapi_app/models/upload_job_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Enum, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum


class UploadJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadJobStep(str, enum.Enum):
    UPLOAD = "upload"
    READ = "read"
    VALIDATE = "validate"
    STORE = "store"
    COMPLETE = "complete"


class UploadJob(Base):
    """Upload processing job."""
    __tablename__ = "upload_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    
    status = Column(Enum(UploadJobStatus), default=UploadJobStatus.QUEUED)
    current_step = Column(Enum(UploadJobStep), default=UploadJobStep.UPLOAD)
    progress_percentage = Column(Float, default=0.0)
    
    records_processed = Column(Integer, default=0)
    records_total = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    upload = relationship("Upload", back_populates="upload_jobs")
    upload_job_steps = relationship(
        "UploadJobStepDetail",
        back_populates="upload_job",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_upload_jobs_upload', 'upload_id'),
        Index('idx_upload_jobs_status', 'status'),
        Index('idx_upload_jobs_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<UploadJob(id={self.id}, job_id={self.job_id}, status={self.status})>"


class UploadJobStepDetail(Base):
    """Individual steps within an upload job."""
    __tablename__ = "upload_job_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_job_id = Column(Integer, ForeignKey("upload_jobs.id", ondelete="CASCADE"), index=True)
    
    step_name = Column(Enum(UploadJobStep), nullable=False)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    
    # Relationships
    upload_job = relationship("UploadJob", back_populates="upload_job_steps")
    
    def __repr__(self):
        return f"<UploadJobStepDetail(id={self.id}, step_name={self.step_name}, status={self.status})>"