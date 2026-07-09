from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from fastapi_app.db.session import Base


class OtpRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)

    # The 6-digit OTP (stored as plain string; short-lived)
    otp_code = Column(String(10), nullable=False)

    # Which user this OTP belongs to (via email lookup) — OTP is delivered
    # by email (see utils/email_utils.py), not SMS, so there's no
    # phone_number column here anymore.
    user_email = Column(String(255), nullable=False, index=True)

    # What this OTP is for — "registration" (verifying a new email before
    # account creation) or "password_reset" (existing account resetting
    # their password). Keeps both flows sharing one table without a
    # registration OTP being usable to reset an unrelated account's password.
    purpose = Column(String(32), nullable=False, default="password_reset")

    # Has this OTP been used already?
    is_used = Column(Boolean, default=False, nullable=False)

    # When this OTP expires (typically now + 10 minutes)
    expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<OtpRecord(id={self.id}, email={self.user_email}, used={self.is_used})>"
        )