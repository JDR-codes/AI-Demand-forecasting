from sqlalchemy import Column, Integer, String
from fastapi_app.db.session import Base


class ValidationError(Base):
    __tablename__ = "validation_errors"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), nullable=False)
    error_type = Column(String(255), nullable=False)
    severity = Column(String(50), default="medium", nullable=False)
    rows_affected = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="open", nullable=False)

    def __repr__(self):
        return f"<ValidationError(id={self.id}, source={self.source}, status={self.status})>"
