#fastapi_app/models/validation_error_model.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Boolean
from fastapi_app.db.session import Base
from datetime import datetime
from sqlalchemy.orm import relationship

class ValidationError(Base):
    __tablename__ = "validation_errors"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), nullable=False)
    error_type = Column(String(255), nullable=False)
    severity = Column(String(50), default="medium", nullable=False)
    rows_affected = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="open", nullable=False)
    
    # Foreign keys
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    sync_id = Column(Integer, ForeignKey("sync_logs.id"), nullable=True)
    
    # Detailed validation fields
    column_name = Column(String(100), nullable=True)
    row_number = Column(Integer, nullable=True)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    
    # ✅ New fields for ignore/fix tracking
    ignored_reason = Column(Text, nullable=True)
    fixed_reason = Column(Text, nullable=True)
    fixed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    fixed_time = Column(DateTime, nullable=True)
    is_ignored = Column(Boolean, default=False)
    is_fixed = Column(Boolean, default=False)
    
    # Resolution tracking
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    datasource = relationship("DataSource", back_populates="validation_errors")
    upload = relationship("Upload", back_populates="validation_errors")
    sync_log = relationship("SyncLog", back_populates="validation_errors")
    resolver = relationship("User", foreign_keys=[resolved_by])
    fixer = relationship("User", foreign_keys=[fixed_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_valerror_datasource', 'datasource_id'),
        Index('idx_valerror_upload', 'upload_id'),
        Index('idx_valerror_sync', 'sync_id'),
        Index('idx_valerror_status', 'status'),
        Index('idx_valerror_severity', 'severity'),
        Index('idx_valerror_is_ignored', 'is_ignored'),
        Index('idx_valerror_is_fixed', 'is_fixed'),
    )

    def __repr__(self):
        return f"<ValidationError(id={self.id}, source={self.source}, status={self.status})>"