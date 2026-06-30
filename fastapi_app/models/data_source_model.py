from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from fastapi_app.db.session import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    connection_string = Column(String(1024), nullable=False)
    status = Column(String(50), default="inactive", nullable=False)
    health = Column(String(50), default="unknown", nullable=False)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, status={self.status})>"
