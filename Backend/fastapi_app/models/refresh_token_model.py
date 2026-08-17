from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime

from fastapi_app.db.session import Base


class RefreshToken(Base):
    """
    Tracks every refresh token that's been issued, so we can:
      - revoke a specific one on logout
      - revoke the *previous* one whenever it's rotated (i.e. exchanged for
        a new access+refresh pair via /refresh-token), so an old refresh
        token can't be replayed after a newer one has been issued from it.

    We store the token's JWT ID (`jti`), not the token itself — the JWT
    stays self-contained (still carries its own exp/signature), this table
    is purely a revocation list.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)

    jti = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<RefreshToken(jti={self.jti}, user_id={self.user_id}, revoked={self.revoked})>"