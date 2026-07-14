# fastapi_app/models/validation_error_model.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from fastapi_app.db.session import Base
from datetime import datetime

class ValidationError(Base):
    __tablename__ = "validation_errors"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), nullable=False)
    error_type = Column(String(255), nullable=False)
    severity = Column(String(50), default="medium", nullable=False)
    rows_affected = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="open", nullable=False)
    
    # New detailed validation fields
    column_name = Column(String(100), nullable=True)
    row_number = Column(Integer, nullable=True)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ValidationError(id={self.id}, source={self.source}, status={self.status})>"