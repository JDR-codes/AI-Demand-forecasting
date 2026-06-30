from sqlalchemy import Column, Integer, String, DateTime
from fastapi_app.db.session import Base
from datetime import datetime


class Permission(Base):
    """A single fine-grained permission, e.g. 'users:read', 'forecast:run'.

    Permissions are a fixed catalog seeded by the app (see db/session.py ->
    _seed_rbac_defaults). They are exposed read-only via GET /api/v1/permissions
    and are assigned to Roles through the role_permissions association table
    in role_model.py.
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"