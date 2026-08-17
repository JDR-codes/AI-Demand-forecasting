#fastapi_app/models/sync_log_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship

class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")
    
    rows_processed = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    rows_validated = Column(Integer, default=0)
    
    message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    duration_seconds = Column(Float, nullable=True)
    triggered_by = Column(String(50), default="manual")  # manual, scheduled, upload
    
    # Relationships
    datasource = relationship("DataSource", back_populates="sync_logs")
    upload = relationship("Upload", back_populates="sync_logs")
    raw_sales = relationship("RawSales", back_populates="sync_log")
    raw_inventory = relationship("RawInventory", back_populates="sync_log")
    raw_suppliers = relationship("RawSupplier", back_populates="sync_log")
    raw_products = relationship("RawProducts", back_populates="sync_log")
    validation_errors = relationship("ValidationError", back_populates="sync_log")  # ✅ Added
    
    # Indexes
    __table_args__ = (
        Index('idx_synclog_datasource', 'datasource_id'),
        Index('idx_synclog_upload', 'upload_id'),
        Index('idx_synclog_status', 'status'),
        Index('idx_synclog_started', 'started_at'),
    )
    
    def __repr__(self):
        return f"<SyncLog(id={self.id}, datasource_id={self.datasource_id}, upload_id={self.upload_id}, status={self.status})>"