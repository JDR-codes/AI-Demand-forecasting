#fastapi_app/models/upload_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Index, Float
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    unique_filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_url = Column(String(1024), nullable=False)
    
    # Metadata fields
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    checksum = Column(String(64), nullable=True)
    extension = Column(String(20), nullable=True)
    
    # Progress fields
    processing_progress = Column(Float, default=0.0)
    processing_status = Column(String(50), default="pending")
    duration_seconds = Column(Float, nullable=True)
    rows = Column(Integer, nullable=True)
    columns = Column(Integer, nullable=True)
    
    status = Column(String(50), default="pending", nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    sync_logs = relationship("SyncLog", back_populates="upload")
    raw_sales = relationship("RawSales", back_populates="upload")
    raw_inventory = relationship("RawInventory", back_populates="upload")
    raw_suppliers = relationship("RawSupplier", back_populates="upload")
    raw_products = relationship("RawProducts", back_populates="upload")
    validation_errors = relationship("ValidationError", back_populates="upload")
    upload_jobs = relationship("UploadJob", back_populates="upload")
    
    # Indexes
    __table_args__ = (
        Index('idx_upload_status', 'status'),
        Index('idx_upload_uploaded_at', 'uploaded_at'),
        Index('idx_upload_uploaded_by', 'uploaded_by'),
        Index('idx_upload_processing_status', 'processing_status'),
    )

    def __repr__(self):
        return f"<Upload(id={self.id}, filename={self.filename}, status={self.status})>"