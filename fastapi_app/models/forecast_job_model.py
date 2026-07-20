# fastapi_app/models/forecast_job_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Text, Boolean, Enum, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum


class ForecastJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ForecastJobStep(str, enum.Enum):
    LOADING_DATA = "loading_data"
    LOADING_MODEL = "loading_model"
    VALIDATING_DATA = "validating_data"
    RUNNING_MODEL = "running_model"
    GENERATING_OUTPUT = "generating_output"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"


class ForecastJob(Base):
    """Main forecast job entity - tracks the entire forecasting run."""
    __tablename__ = "forecast_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    
    # References
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    model_registry_id = Column(String(36), ForeignKey("model_registry.id"), nullable=True)
    
    # ✅ REMOVED - Table 'processing_pipelines' doesn't exist
    # processing_pipeline_id = Column(Integer, ForeignKey("processing_pipelines.id"), nullable=True)
    
    # Status
    status = Column(Enum(ForecastJobStatus), default=ForecastJobStatus.QUEUED)
    progress_percentage = Column(Float, default=0.0)
    current_step = Column(Integer, default=0)
    current_step_name = Column(String(100), nullable=True)
    
    # Failed step tracking
    failed_step = Column(Integer, nullable=True)
    failed_step_name = Column(String(100), nullable=True)
    current_step_message = Column(String(255), nullable=True)
    
    # Configuration
    forecast_horizon = Column(Integer, default=7)
    configuration = Column(JSON, nullable=True)
    
    # SKU/Region/Warehouse filtering
    sku = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    warehouse = Column(String(100), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    elapsed_time = Column(Float, nullable=True)
    remaining_seconds = Column(Float, nullable=True)
    
    # Forecast date range
    forecast_start_date = Column(DateTime, nullable=True)
    forecast_end_date = Column(DateTime, nullable=True)
    
    # Results
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    upload = relationship("Upload")
    model_registry = relationship("ModelRegistry", back_populates="forecast_jobs")
    creator = relationship("User", foreign_keys=[created_by])
    forecast_results = relationship(
        "ForecastResult",
        back_populates="forecast_job",
        cascade="all, delete-orphan"
    )
    job_steps = relationship(
        "ForecastJobStepDetail",  # ✅ Fixed
        back_populates="forecast_job",
        cascade="all, delete-orphan"
    )
    # Indexes
    __table_args__ = (
        Index('idx_forecast_jobs_status', 'status'),
        Index('idx_forecast_jobs_created_at', 'created_at'),
        Index('idx_forecast_jobs_model_registry_id', 'model_registry_id'),
        Index('idx_forecast_jobs_upload_id', 'upload_id'),
        Index('idx_forecast_jobs_sku', 'sku'),
        Index('idx_forecast_jobs_region', 'region'),
    )
    
    def __repr__(self):
        return f"<ForecastJob(id={self.id}, job_id={self.job_id}, status={self.status})>"


class ForecastJobStepDetail(Base):
    """Individual steps within a forecast job."""
    __tablename__ = "forecast_job_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    forecast_job_id = Column(Integer, ForeignKey("forecast_jobs.id", ondelete="CASCADE"), index=True)
    
    step_number = Column(Integer, nullable=False)
    step_name = Column(Enum(ForecastJobStep), nullable=False)
    status = Column(String(50), default="pending")
    progress = Column(Float, default=0.0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    
    # Relationships
    forecast_job = relationship("ForecastJob", back_populates="job_steps")
    
    __table_args__ = (
        Index('idx_forecast_job_steps_job', 'forecast_job_id'),
        Index('idx_forecast_job_steps_status', 'status'),
    )
    
    def __repr__(self):
        return f"<ForecastJobStepDetail(id={self.id}, step_name={self.step_name}, status={self.status})>"


class ForecastResult(Base):
    """Individual forecast results."""
    __tablename__ = "forecast_results"
    
    id = Column(Integer, primary_key=True, index=True)
    forecast_job_id = Column(Integer, ForeignKey("forecast_jobs.id", ondelete="CASCADE"), index=True)
    
    sku = Column(String(100), nullable=False, default="default")
    region = Column(String(100), nullable=True)
    warehouse = Column(String(100), nullable=True)
    
    forecast_date = Column(DateTime, nullable=False)
    prediction = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=True)
    
    confidence_upper = Column(Float, nullable=True)
    confidence_lower = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Flag to distinguish historical from forecast
    is_forecast = Column(Boolean, default=True)
    is_peak = Column(Boolean, default=False)
    
    model_used = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    forecast_job = relationship("ForecastJob", back_populates="forecast_results")
    
    __table_args__ = (
        Index('idx_forecast_results_job', 'forecast_job_id'),
        Index('idx_forecast_results_date', 'forecast_date'),
        Index('idx_forecast_results_sku', 'sku'),
        Index('idx_forecast_results_is_forecast', 'is_forecast'),
    )
    
    def __repr__(self):
        return f"<ForecastResult(id={self.id}, date={self.forecast_date}, prediction={self.prediction})>"