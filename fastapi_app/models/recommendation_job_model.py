#fastapi_app/models/recommendation_job_model.py
"""
Recommendation Job Model - Tracks recommendation generation jobs.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Enum, Index, JSON
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum
import uuid


class RecommendationJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecommendationJobStep(str, enum.Enum):
    LOADING_FORECAST = "loading_forecast"
    LOADING_SUMMARY = "loading_summary"
    READING_RESULTS = "reading_results"
    DEMAND_ANALYSIS = "demand_analysis"
    INVENTORY_ANALYSIS = "inventory_analysis"
    RISK_ANALYSIS = "risk_analysis"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    REMOVING_DUPLICATES = "removing_duplicates"
    VALIDATING = "validating"
    SAVING_RECOMMENDATIONS = "saving_recommendations"
    NOTIFYING = "notifying"
    REFRESHING_DASHBOARD = "refreshing_dashboard"
    COMPLETED = "completed"


class RecommendationJob(Base):
    """Recommendation generation job."""
    __tablename__ = "recommendation_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # References
    forecast_job_id = Column(String(36), ForeignKey("forecast_jobs.job_id"), nullable=False)
    forecast_job_internal_id = Column(Integer, ForeignKey("forecast_jobs.id"), nullable=True)
    
    # Status
    status = Column(Enum(RecommendationJobStatus), default=RecommendationJobStatus.QUEUED)
    progress_percentage = Column(Float, default=0.0)
    current_step = Column(Integer, default=0)
    current_step_name = Column(String(100), nullable=True)
    
    # Failed step tracking
    failed_step = Column(Integer, nullable=True)
    failed_step_name = Column(String(100), nullable=True)
    current_step_message = Column(String(255), nullable=True)
    
    # Counts
    total_recommendations = Column(Integer, default=0)
    saved_recommendations = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    
    # Metrics
    forecast_summary = Column(JSON, nullable=True)
    analysis_version = Column(String(20), default="1.0.0")
    generator_version = Column(String(20), default="1.0.0")
    recommendation_score = Column(Float, default=0.0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    elapsed_time = Column(Float, nullable=True)
    remaining_seconds = Column(Float, nullable=True)
    total_processing_time = Column(Float, nullable=True)
    job_duration = Column(Float, nullable=True)
    
    # User
    started_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Results
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    forecast_job = relationship("ForecastJob", foreign_keys=[forecast_job_internal_id])
    creator = relationship("User", foreign_keys=[created_by])
    started_by_user = relationship("User", foreign_keys=[started_by])
    recommendation_steps = relationship(
        "RecommendationJobStepDetail",
        back_populates="recommendation_job",
        cascade="all, delete-orphan"
    )
    recommendation_results = relationship(
        "RecommendationResult",
        back_populates="recommendation_job",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_rec_jobs_status', 'status'),
        Index('idx_rec_jobs_forecast_job_id', 'forecast_job_id'),
        Index('idx_rec_jobs_created_at', 'created_at'),
        Index('idx_rec_jobs_created_by', 'created_by'),
        Index('idx_rec_jobs_started_by', 'started_by'),
    )
    
    def __repr__(self):
        return f"<RecommendationJob(id={self.id}, job_id={self.job_id}, status={self.status})>"


class RecommendationJobStepDetail(Base):
    """Individual steps within a recommendation job."""
    __tablename__ = "recommendation_job_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    recommendation_job_id = Column(Integer, ForeignKey("recommendation_jobs.id", ondelete="CASCADE"), index=True)
    
    step_number = Column(Integer, nullable=False)
    step_name = Column(Enum(RecommendationJobStep), nullable=False)
    status = Column(String(50), default="pending")
    progress = Column(Float, default=0.0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    
    # Relationships
    recommendation_job = relationship("RecommendationJob", back_populates="recommendation_steps")
    
    __table_args__ = (
        Index('idx_rec_job_steps_job', 'recommendation_job_id'),
        Index('idx_rec_job_steps_status', 'status'),
    )
    
    def __repr__(self):
        return f"<RecommendationJobStepDetail(id={self.id}, step_name={self.step_name}, status={self.status})>"