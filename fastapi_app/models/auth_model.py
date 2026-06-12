from sqlalchemy import Column, Integer, String, Boolean, DateTime
from fastapi_app.db.session import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)

    email = Column(String(255), unique=True, nullable=False)

    password = Column(String(255), nullable=False)

    role = Column(String(50), default="user", nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"