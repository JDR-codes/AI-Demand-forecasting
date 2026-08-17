from sqlalchemy import Column, Integer, String, DateTime
from fastapi_app.db.session import Base
from datetime import datetime


class Permission(Base):
    """A single fine-grained permission, e.g. 'users:read', 'forecast:run'.

    Permissions are a fixed catalog seeded by the application.
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"