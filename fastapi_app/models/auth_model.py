from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from fastapi_app.db.session import Base
from fastapi_app.models.role_model import Role
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)

    email = Column(String(255), unique=True, nullable=False)

    password = Column(String(255), nullable=False)

    initial_password_hash = Column(String(255), nullable=True)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    role = relationship("Role", back_populates="users", lazy="joined")

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @hybrid_property
    def is_admin(self) -> bool:
        return bool(self.role and self.role.name in ("admin", "super_admin"))

    @is_admin.expression
    def is_admin(cls):
        return cls.role.has(Role.name.in_(["admin", "super_admin"]))

    def __repr__(self):
        role_name = self.role.name if self.role else None
        return f"<User(id={self.id}, email={self.email}, role={role_name})>"