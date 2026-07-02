"""
Password reset service — OTP-based, sent to the user's email via SMTP.

Flow:
    1. request_otp()    — look up user by email, generate OTP, persist it,
                           and email it to the user via SMTP.
    2. verify_otp()     — validate OTP, mark used, return a short-lived JWT reset_token
    3. reset_password() — validate reset_token, update user password
"""

import random
import string
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from fastapi_app.models.auth_model import User
from fastapi_app.models.otp_model import OtpRecord
from fastapi_app.core.security import hash_password, create_access_token, verify_token
from fastapi_app.utils.email_utils import send_otp_email

# OTP valid for 10 minutes
OTP_EXPIRY_MINUTES = 10

# Reset token valid for 15 minutes (issued after OTP is verified)
RESET_TOKEN_EXPIRY_MINUTES = 15


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of the given length."""
    return "".join(random.choices(string.digits, k=length))


# ---------------------------------------------------------------------------
# Step 1: request OTP
# ---------------------------------------------------------------------------

def request_password_reset_otp(db: Session, email: str) -> dict:
    """
    Look up the user, generate a 6-digit OTP, persist it, and email it
    to the user via SMTP.
    """
    generic_response = {
        "message": "If an account with that email exists, an OTP has been sent to it.",
    }

    user: User | None = (
        db.query(User)
        .filter(User.email == email, User.is_active == True)
        .first()
    )

    if not user:
        return generic_response

    # Invalidate any previous unused OTPs for this email
    db.query(OtpRecord).filter(
        OtpRecord.user_email == email,
        OtpRecord.is_used == False,
    ).update({"is_used": True})
    db.commit()

    otp_code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp_record = OtpRecord(
        otp_code=otp_code,
        user_email=email,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(otp_record)
    db.commit()

    try:
        send_otp_email(email, otp_code, expiry_minutes=OTP_EXPIRY_MINUTES)
    except Exception as exc:
        # Roll back the OTP so a failed email doesn't leave a "valid" but
        # never-delivered OTP sitting in the database.
        otp_record.is_used = True
        db.commit()
        raise ValueError(f"Failed to send OTP email: {exc}")

    return {
        "message": "An OTP has been sent to your email address.",
    }


# ---------------------------------------------------------------------------
# Step 2: verify OTP → issue reset token
# ---------------------------------------------------------------------------

def verify_reset_otp(db: Session, email: str, otp_code: str) -> str:
    """
    Validate the OTP and return a short-lived JWT reset_token.

    Raises ValueError with a user-facing message on any failure.
    """
    otp_record: OtpRecord | None = (
        db.query(OtpRecord)
        .filter(
            OtpRecord.user_email == email,
            OtpRecord.otp_code == otp_code,
            OtpRecord.is_used == False,
        )
        .order_by(OtpRecord.created_at.desc())
        .first()
    )

    if not otp_record:
        raise ValueError("Invalid OTP. Please request a new one.")

    if datetime.utcnow() > otp_record.expires_at:
        otp_record.is_used = True
        db.commit()
        raise ValueError("OTP has expired. Please request a new one.")

    # Mark OTP as consumed
    otp_record.is_used = True
    db.commit()

    # Issue a short-lived token scoped to password reset only
    reset_token = create_access_token(
        data={"sub": email, "purpose": "password_reset"},
        expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    )

    return reset_token


# ---------------------------------------------------------------------------
# Step 3: reset password using reset_token
# ---------------------------------------------------------------------------

def reset_user_password(db: Session, email: str, reset_token: str, new_password: str) -> None:
    """
    Validate the reset_token and update the user's password.

    Raises ValueError with a user-facing message on any failure.
    """
    try:
        payload = verify_token(reset_token)
    except ValueError as exc:
        raise ValueError(str(exc))

    # Ensure the token was issued for password_reset and for this email
    if payload.get("purpose") != "password_reset":
        raise ValueError("Invalid reset token.")

    if payload.get("sub") != email:
        raise ValueError("Token does not match the provided email.")

    user: User | None = (
        db.query(User)
        .filter(User.email == email, User.is_active == True)
        .first()
    )

    if not user:
        raise ValueError("User not found.")

    new_password_hash = hash_password(new_password)

    # Block reuse of the current password.
    if user.password == new_password_hash:
        raise ValueError("New password must be different from your current password.")

    # Block reuse of the password the account was originally created with
    # (set by the admin, or at self-registration).
    if user.initial_password_hash and user.initial_password_hash == new_password_hash:
        raise ValueError(
            "This is the password your account was created with. Please choose a different password."
        )

    user.password = new_password_hash
    db.commit()