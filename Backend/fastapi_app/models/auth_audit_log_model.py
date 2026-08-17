from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from fastapi_app.db.session import Base


class AuditLog(Base):
    """
    Comprehensive audit log for all significant actions:
    - Authentication events (login, logout, token refresh)
    - User management (create, update, delete, activate, deactivate)
    - Role management (create, update, delete, permission changes)
    - Security events (access denied, protected role attempts)
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who performed the action
    user_id = Column(Integer, nullable=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    user_role = Column(String(100), nullable=True)
    
    # What happened
    event_type = Column(String(64), nullable=False, index=True)
    # e.g., "login_success", "login_failed", "user_created", "user_updated", 
    # "user_deleted", "role_permissions_updated", "access_denied"
    
    success = Column(Boolean, nullable=False, default=True)
    action = Column(String(255), nullable=True)  # Human-readable action description
    
    # Target
    target_type = Column(String(64), nullable=True)  # "user", "role", "permission", etc.
    target_id = Column(Integer, nullable=True)
    target_name = Column(String(255), nullable=True)
    
    # Context
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    detail = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog(event={self.event_type}, user={self.user_email}, success={self.success})>"