import hashlib
from datetime import datetime, timedelta
from typing import Any

import jwt

from fastapi_app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE


def hash_password(password: str) -> str:
    """Hash a plain-text password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plain-text password matches a hashed password."""
    return hash_password(plain_password) == hashed_password


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token containing payload data."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
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
