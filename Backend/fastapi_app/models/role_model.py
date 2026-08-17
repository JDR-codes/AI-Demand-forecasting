# fastapi_app/models/role_model.py
from sqlalchemy import JSON, Boolean, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from fastapi_app.db.session import Base
from datetime import datetime

# Many-to-many association between roles and permissions.
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    """A named, admin-manageable group of Permissions."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False, default="")
    description = Column(String(255), nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)
    
    # ──────────────────────────────────────────────────────────────────────────
    # ROLE-LEVEL ACCESS CONTROL SETTINGS (from Access Controls tab)
    # These are applied to ALL users with this role
    # ──────────────────────────────────────────────────────────────────────────
    login_enabled = Column(Boolean, default=True, nullable=False)      # "Platform Login" toggle
    require_mfa = Column(Boolean, default=False, nullable=False)        # "Require MFA" toggle
    ip_restriction_enabled = Column(Boolean, default=False, nullable=False)  # "IP Restriction" toggle
    allowed_ip_ranges = Column(JSON, nullable=True)                    # IP whitelist ranges
    session_timeout_hours = Column(Integer, default=8, nullable=False)  # Session timeout
    max_concurrent_sessions = Column(Integer, default=3, nullable=False)  # Max concurrent sessions
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        backref="roles",
        lazy="joined",
    )
    
    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name}, display_name={self.display_name})>"