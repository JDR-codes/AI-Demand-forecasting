from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime

from fastapi_app.db.session import Base


class AuthAuditLog(Base):
    """
    A record of every significant authentication event — registration,
    OTP requests/verifications, login attempts (success and failure),
    token refreshes, and logouts. Kept even for events on emails that
    don't correspond to a real user (e.g. failed login on unknown email),
    so brute-force / enumeration attempts are visible too.
    """
    __tablename__ = "auth_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    # e.g. "register_requested", "register_otp_verified", "login_success",
    # "login_failed", "token_refresh", "logout"

    success = Column(Boolean, nullable=False, default=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    detail = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuthAuditLog(event={self.event_type}, email={self.email}, success={self.success})>"