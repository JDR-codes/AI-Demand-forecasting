import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
import bcrypt

from fastapi_app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE

_BCRYPT_MAX_PASSWORD_BYTES = 72  # bcrypt's hard limit


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_PASSWORD_BYTES]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def is_legacy_sha256_hash(hashed_password: str) -> bool:
    """A bare SHA-256 hex digest is 64 characters of hex and won't match the
    bcrypt '$2b$...' format — used to detect old, pre-bcrypt password hashes."""
    return len(hashed_password) == 64 and all(c in "0123456789abcdef" for c in hashed_password.lower())


def _legacy_sha256_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored hash. Supports both the
    current bcrypt format and legacy SHA-256 hashes from before this change."""
    if is_legacy_sha256_hash(hashed_password):
        return _legacy_sha256_hash(plain_password) == hashed_password
    pw_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed/unrecognized hash format stored in the DB — fail closed.
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token containing payload data. Always stamps a
    unique 'jti' so every issued token (access, refresh, or OTP-session) can
    be individually identified/revoked if needed."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire, "jti": to_encode.get("jti") or str(uuid.uuid4())})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    """Verify a JWT token and return its payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")