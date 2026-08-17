# fastapi_app/models/training_job_model.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, ForeignKey, Text, Enum, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum


class TrainingStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingStep(str, enum.Enum):
    PROCESSING_DATA = "processing_data"
    VALIDATION = "validation"
    TRAINING = "training"
    EVALUATION = "evaluation"
    SAVING_MODEL = "saving_model"
    COMPLETED = "completed"


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    job_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)    
    model_registry_id = Column(String(36), ForeignKey("model_registry.id"), nullable=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    processing_job_id = Column(String(50), nullable=True)
    
    model_type = Column(String(50), nullable=False)
    status = Column(Enum(TrainingStatus), default=TrainingStatus.QUEUED)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    current_epoch = Column(Integer, default=0)
    total_epochs = Column(Integer, nullable=True)
    current_step = Column(String(100), nullable=True)
    current_step_name = Column(String(100), nullable=True)
    
    # ✅ Failed step tracking
    failed_step = Column(Integer, nullable=True)
    failed_step_name = Column(String(100), nullable=True)
    current_step_message = Column(String(255), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    elapsed_time = Column(Float, nullable=True)
    remaining_time = Column(Float, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    worker_name = Column(String(100), nullable=True)
    
    # Metrics
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Configuration - stores batch_size, learning_rate, epochs, etc.
    configuration = Column(JSON, nullable=True)
    
    # Metadata
    csv_path = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    model_registry = relationship("ModelRegistry", back_populates="training_jobs")
    upload = relationship("Upload")
    training_history = relationship("TrainingHistory", back_populates="training_job", cascade="all, delete-orphan")
    training_steps = relationship("TrainingJobStepDetail", back_populates="training_job", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_training_jobs_status', 'status'),
        Index('idx_training_jobs_model_type', 'model_type'),
        Index('idx_training_jobs_created_at', 'created_at'),
        Index('idx_training_jobs_model_registry_id', 'model_registry_id'),
    )
    
    @property
    def created_by(self):
        if self.configuration and isinstance(self.configuration, dict):
            return self.configuration.get("created_by")
        return None

    def __repr__(self):
        return f"<TrainingJob(job_id={self.job_id}, model_type={self.model_type}, status={self.status})>"


class TrainingJobStepDetail(Base):
    """Individual steps within a training job."""
    __tablename__ = "training_job_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    training_job_id = Column(String(36), ForeignKey("training_jobs.job_id", ondelete="CASCADE"), index=True)
    
    step_number = Column(Integer, nullable=False)
    step_name = Column(Enum(TrainingStep), nullable=False)
    status = Column(String(50), default="pending")
    progress = Column(Float, default=0.0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    
    # Relationships
    training_job = relationship("TrainingJob", back_populates="training_steps")
    
    def __repr__(self):
        return f"<TrainingJobStepDetail(id={self.id}, step_name={self.step_name}, status={self.status})>"


class TrainingHistory(Base):
    """Retraining history for model version tracking."""
    __tablename__ = "training_history"
    
    id = Column(Integer, primary_key=True, index=True)
    training_job_id = Column(String(36), ForeignKey("training_jobs.job_id", ondelete="SET NULL"), nullable=True)
    model_registry_id = Column(String(36), ForeignKey("model_registry.id", ondelete="SET NULL"), nullable=True)
    
    version = Column(String(50), nullable=False)
    
    # ✅ Extended metrics
    accuracy_before = Column(Float, nullable=True)
    accuracy_after = Column(Float, nullable=True)
    improvement_percentage = Column(Float, nullable=True)
    
    rmse_before = Column(Float, nullable=True)
    rmse_after = Column(Float, nullable=True)
    mae_before = Column(Float, nullable=True)
    mae_after = Column(Float, nullable=True)
    mape_before = Column(Float, nullable=True)
    mape_after = Column(Float, nullable=True)
    
    duration_seconds = Column(Float, nullable=True)
    epochs = Column(Integer, nullable=True)
    dataset_size = Column(Integer, nullable=True)
    
    status = Column(String(50), default="completed")
    
    trained_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    trained_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    
    # Relationships
    training_job = relationship("TrainingJob", back_populates="training_history")
    model_registry = relationship("ModelRegistry", back_populates="training_history")
    trainer = relationship("User", foreign_keys=[trained_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_training_history_model_registry_id', 'model_registry_id'),
        Index('idx_training_history_trained_at', 'trained_at'),
        Index('idx_training_history_version', 'version'),
        Index('idx_training_history_training_job_id', 'training_job_id'),
    )
    
    def __repr__(self):
        return f"<TrainingHistory(id={self.id}, version={self.version}, status={self.status})>"