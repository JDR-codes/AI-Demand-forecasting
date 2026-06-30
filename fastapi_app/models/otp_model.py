from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from fastapi_app.db.session import Base


class OtpRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)

    # The 6-digit OTP (stored as plain string; short-lived)
    otp_code = Column(String(10), nullable=False)

    # Which user this OTP belongs to (via email lookup) — OTP is delivered
    # by email (see services/auth/email_service.py), not SMS, so there's no
    # phone_number column here anymore.
    user_email = Column(String(255), nullable=False, index=True)

    # Has this OTP been used already?
    is_used = Column(Boolean, default=False, nullable=False)

    # When this OTP expires (typically now + 10 minutes)
    expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<OtpRecord(id={self.id}, email={self.user_email}, used={self.is_used})>"
        )