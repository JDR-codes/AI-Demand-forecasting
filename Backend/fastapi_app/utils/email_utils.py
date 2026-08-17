"""
Email sending utility — delivers the password-reset OTP by email via SMTP.

Configure via these .env variables:

    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your_email@gmail.com
    SMTP_PASS=your_16_char_app_password   # NOT your normal Gmail password —
                                           # generate one at
                                           # https://myaccount.google.com/apppasswords
    EMAIL_FROM=your_email@gmail.com       # optional, defaults to SMTP_USER
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi_app.core.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM


def send_otp_email(to_email: str, otp_code: str, expiry_minutes: int = 10) -> None:
    """Send a 6-digit OTP code to `to_email` via SMTP. Raises an exception on
    any failure (missing config, auth failure, connection error, etc) —
    callers should catch this (see password_reset_service.py)."""
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError(
            "SMTP_USER / SMTP_PASS are not configured in .env — cannot send email."
        )

    subject = "Your password reset OTP"
    body = (
        f"Your OTP for resetting your password is: {otp_code}\n\n"
        f"This code expires in {expiry_minutes} minutes. If you didn't request "
        f"this, you can safely ignore this email."
    )

    message = MIMEMultipart()
    message["From"] = EMAIL_FROM or SMTP_USER
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM or SMTP_USER, to_email, message.as_string())