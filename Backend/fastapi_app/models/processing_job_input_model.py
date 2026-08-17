# fastapi_app/models/processing_job_input_model.py
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
)
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship


class ProcessingJobInput(Base):
    __tablename__ = "processing_job_inputs"

    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(
        Integer,
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    input_type = Column(
        String(30),
        nullable=False
    )
    data_source_id = Column(
        Integer,
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    upload_id = Column(
        Integer,
        ForeignKey("uploads.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    category = Column(
        String(50),
        nullable=False,
        index=True
    )
    status = Column(
        String(30),
        nullable=False,
        default="pending"
    )
    records_loaded = Column(
        Integer,
        nullable=False,
        default=0
    )
    records_processed = Column(
        Integer,
        nullable=False,
        default=0
    )
    error_message = Column(
        Text,
        nullable=True
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    started_at = Column(
        DateTime,
        nullable=True
    )
    completed_at = Column(
        DateTime,
        nullable=True
    )

    processing_job = relationship("ProcessingJob", back_populates="processing_inputs")

    def __repr__(self):
        return f"<ProcessingJobInput(id={self.id}, type={self.input_type}, category={self.category}, status={self.status})>"
