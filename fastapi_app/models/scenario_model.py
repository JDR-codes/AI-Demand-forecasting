from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, DateTime, JSON

from fastapi_app.db.session import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    parameters = Column(JSON, nullable=True)
    status = Column(String(50), default="created", nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(50), nullable=True)
    last_run_output = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, name={self.name}, status={self.status})>"
