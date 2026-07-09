import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from fastapi_app.db.session import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    model_type = Column(String(50), nullable=False)
    version = Column(String(50), nullable=True)
    path = Column(String(1024), nullable=True)
    meta_info = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
