# fastapi_app/models/sync_log_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship

class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    # Make datasource_id nullable for uploads
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)  # ✅ Changed to nullable=True
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # running, success, failed, partial_success
    
    rows_processed = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    rows_validated = Column(Integer, default=0)
    
    message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Performance metrics
    duration_seconds = Column(Float, nullable=True)
    
    # Relationships
    datasource = relationship("DataSource", back_populates="sync_logs")
    raw_sales = relationship("RawSales", back_populates="sync_log")
    raw_inventory = relationship("RawInventory", back_populates="sync_log")
    raw_suppliers = relationship("RawSupplier", back_populates="sync_log")
    raw_products = relationship("RawProducts", back_populates="sync_log")
    
    def __repr__(self):
        return f"<SyncLog(id={self.id}, datasource_id={self.datasource_id}, status={self.status})>"