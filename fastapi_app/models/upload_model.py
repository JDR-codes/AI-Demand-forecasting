from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from fastapi_app.db.session import Base


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    uploaded_by = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Upload(id={self.id}, filename={self.filename}, status={self.status})>"
