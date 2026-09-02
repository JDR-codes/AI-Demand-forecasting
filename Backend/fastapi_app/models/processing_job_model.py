#fastapi_app/models/processing_job_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Enum, Index, JSON, Boolean
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum


class ProcessingJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJobStep(str, enum.Enum):
    DATA_INGESTION = "data_ingestion"
    SCHEMA_VALIDATION = "schema_validation"
    MISSING_VALUE_IMPUTATION = "missing_value_imputation"
    OUTLIER_DETECTION = "outlier_detection"
    NORMALIZATION_SCALING = "normalization_scaling"
    FEATURE_ENGINEERING = "feature_engineering"
    DATA_AGGREGATION = "data_aggregation"
    COMPLETE = "complete"



class ProcessingJob(Base):
    """Processing pipeline job."""
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    dataset_path = Column(String(1024), nullable=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    
    category_mode = Column(String(20), default="selected")
    categories = Column(JSON, default=list)
    merge_strategy = Column(String(20), default="separate")
    deduplicate = Column(Boolean, default=True)
    run_validation = Column(Boolean, default=True)
    run_outlier_detection = Column(Boolean, default=True)
    run_feature_engineering = Column(Boolean, default=True)
    
    status = Column(Enum(ProcessingJobStatus), default=ProcessingJobStatus.QUEUED)
    current_step = Column(String(50), default=ProcessingJobStep.DATA_INGESTION)
    progress_percentage = Column(Float, default=0.0)
    
    records_loaded = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    eta_seconds = Column(Float, nullable=True)
    
    results = Column(JSON, nullable=True)  # Processing results
    error_message = Column(Text, nullable=True)
    warning_message = Column(Text, nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    upload = relationship("Upload")
    datasource = relationship("DataSource")
    creator = relationship("User", foreign_keys=[created_by])
    processing_steps = relationship(
        "ProcessingJobStepDetail",  # ✅ Fixed
        back_populates="processing_job",
        cascade="all, delete-orphan"
    )
    processing_logs = relationship(
        "ProcessingJobLog",
        back_populates="processing_job",
        cascade="all, delete-orphan"
    )
    outlier_results = relationship(
        "ProcessingOutlierResult",
        back_populates="processing_job",
        cascade="all, delete-orphan"
    )
    generated_features = relationship(
        "ProcessingGeneratedFeature",
        back_populates="processing_job",
        cascade="all, delete-orphan"
    )
    processed_datasets = relationship(
        "ProcessedDataset",
        back_populates="processing_job",
        cascade="all, delete-orphan"
    )
    processing_inputs = relationship(
        "ProcessingJobInput",
        back_populates="processing_job",
        cascade="all, delete-orphan"
    )
    __table_args__ = (
        Index('idx_processing_jobs_status', 'status'),
        Index('idx_processing_jobs_created_at', 'created_at'),
        Index('idx_processing_jobs_upload', 'upload_id'),
        Index('idx_processing_jobs_datasource', 'datasource_id'),
    )
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, job_id={self.job_id}, status={self.status})>"


class ProcessedDataset(Base):
    """Persisted processed dataset artifacts for a processing job."""
    __tablename__ = "processed_datasets"

    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="CASCADE"), index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    file_path = Column(String(1024), nullable=True)
    record_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    processing_job = relationship("ProcessingJob", back_populates="processed_datasets")

    def __repr__(self):
        return f"<ProcessedDataset(id={self.id}, name={self.name}, category={self.category})>"


class ProcessingJobStepDetail(Base):
    """Individual steps within a processing job."""
    __tablename__ = "processing_job_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="CASCADE"), index=True)
    
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")
    progress = Column(Float, default=0.0)
    records_processed = Column(Integer, default=0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    
    # Relationships
    processing_job = relationship("ProcessingJob", back_populates="processing_steps")
    
    def __repr__(self):
        return f"<ProcessingJobStepDetail(id={self.id}, step_name={self.step_name}, status={self.status})>"


class ProcessingJobLog(Base):
    """Logs for processing jobs."""
    __tablename__ = "processing_job_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="CASCADE"), index=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    step = Column(String(100), nullable=True)
    log_metadata = Column(JSON, nullable=True)
    
    # Relationships
    processing_job = relationship("ProcessingJob", back_populates="processing_logs")
    
    __table_args__ = (
        Index('idx_processing_logs_job', 'processing_job_id'),
        Index('idx_processing_logs_timestamp', 'timestamp'),
        Index('idx_processing_logs_level', 'level'),
    )


class ProcessingOutlierResult(Base):
    """Outlier detection results."""
    __tablename__ = "processing_outlier_results"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="CASCADE"), index=True)
    
    column_name = Column(String(100), nullable=False)
    method = Column(String(50), nullable=True)
    total_outliers = Column(Integer, default=0)
    removed = Column(Integer, default=0)
    capped = Column(Integer, default=0)
    normal_values = Column(Integer, default=0)
    percentage_removed = Column(Float, default=0.0)
    percentage_capped = Column(Float, default=0.0)
    spike_rows = Column(JSON, nullable=True)  # List of row indices
    normal_points = Column(JSON, nullable=True)  # Sample of normal values
    outlier_points = Column(JSON, nullable=True)  # Sample of outlier values
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    processing_job = relationship("ProcessingJob", back_populates="outlier_results")
    
    def __repr__(self):
        return f"<ProcessingOutlierResult(id={self.id}, column={self.column_name}, outliers={self.total_outliers})>"


class ProcessingGeneratedFeature(Base):
    """Generated features from processing."""
    __tablename__ = "processing_generated_features"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="CASCADE"), index=True)
    
    name = Column(String(100), nullable=False)
    feature_type = Column(String(50), nullable=False)  # rolling, cyclical, binary, derived
    description = Column(String(255), nullable=True)
    importance = Column(Float, nullable=True)
    data = Column(JSON, nullable=True)  # Sample of feature values
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    processing_job = relationship("ProcessingJob", back_populates="generated_features")
    
    def __repr__(self):
        return f"<ProcessingGeneratedFeature(id={self.id}, name={self.name}, type={self.feature_type})>"