import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from fastapi_app.db.session import Base


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(36), nullable=True)
    csv_path = Column(String(1024), nullable=True)
    model_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
