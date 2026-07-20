#fastapi_app/models/raw_data_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Text, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship

class RawSales(Base):
    __tablename__ = "raw_sales"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)  # ✅ Made nullable
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)  # ✅ Added upload_id
    sync_id = Column(Integer, ForeignKey("sync_logs.id"), nullable=True)
    
    # Data fields - all lowercase
    date = Column(DateTime, nullable=True)
    sku = Column(String(100), nullable=True)
    demand = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    units = Column(Integer, nullable=True)
    
    # Validation details
    column_name = Column(String(100), nullable=True)
    row_number = Column(Integer, nullable=True)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    
    # Metadata
    raw_data = Column(JSON, nullable=True)
    validation_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    datasource = relationship("DataSource", back_populates="raw_sales")
    upload = relationship("Upload", back_populates="raw_sales")  # ✅ Added upload relationship
    sync_log = relationship("SyncLog", back_populates="raw_sales")
    
    # ✅ Add indexes for performance
    __table_args__ = (
        Index('idx_raw_sales_datasource', 'datasource_id'),
        Index('idx_raw_sales_upload', 'upload_id'),
        Index('idx_raw_sales_sync', 'sync_id'),
        Index('idx_raw_sales_date', 'date'),
        Index('idx_raw_sales_sku', 'sku'),
    )


class RawInventory(Base):
    __tablename__ = "raw_inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)  # ✅ Made nullable
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)  # ✅ Added upload_id
    sync_id = Column(Integer, ForeignKey("sync_logs.id"), nullable=True)
    
    # Data fields - all lowercase
    warehouse = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)
    stock = Column(Integer, nullable=True)
    reorder_level = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    
    # Validation details
    column_name = Column(String(100), nullable=True)
    row_number = Column(Integer, nullable=True)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    
    # Metadata
    raw_data = Column(JSON, nullable=True)
    validation_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    datasource = relationship("DataSource", back_populates="raw_inventory")
    upload = relationship("Upload", back_populates="raw_inventory")  # ✅ Added upload relationship
    sync_log = relationship("SyncLog", back_populates="raw_inventory")
    
    __table_args__ = (
        Index('idx_raw_inventory_datasource', 'datasource_id'),
        Index('idx_raw_inventory_upload', 'upload_id'),
        Index('idx_raw_inventory_sync', 'sync_id'),
        Index('idx_raw_inventory_sku', 'sku'),
    )


class RawSupplier(Base):
    __tablename__ = "raw_suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)  # ✅ Made nullable
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)  # ✅ Added upload_id
    sync_id = Column(Integer, ForeignKey("sync_logs.id"), nullable=True)
    
    # Data fields - all lowercase
    supplier = Column(String(255), nullable=True)
    sku = Column(String(100), nullable=True)
    lead_time = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    min_order = Column(Integer, nullable=True)
    
    # Validation details
    column_name = Column(String(100), nullable=True)
    row_number = Column(Integer, nullable=True)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    
    # Metadata
    raw_data = Column(JSON, nullable=True)
    validation_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    datasource = relationship("DataSource", back_populates="raw_suppliers")
    upload = relationship("Upload", back_populates="raw_suppliers")  # ✅ Added upload relationship
    sync_log = relationship("SyncLog", back_populates="raw_suppliers")
    
    __table_args__ = (
        Index('idx_raw_suppliers_datasource', 'datasource_id'),
        Index('idx_raw_suppliers_upload', 'upload_id'),
        Index('idx_raw_suppliers_sync', 'sync_id'),
    )


class RawProducts(Base):
    __tablename__ = "raw_products"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)  # ✅ Made nullable
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)  # ✅ Added upload_id
    sync_id = Column(Integer, ForeignKey("sync_logs.id"), nullable=True)
    
    # Data fields - all lowercase
    sku = Column(String(100), nullable=True)
    name = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    price = Column(Float, nullable=True)
    
    # Validation details
    column_name = Column(String(100), nullable=True)
    row_number = Column(Integer, nullable=True)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    
    # Metadata
    raw_data = Column(JSON, nullable=True)
    validation_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    datasource = relationship("DataSource", back_populates="raw_products")
    upload = relationship("Upload", back_populates="raw_products")  # ✅ Added upload relationship
    sync_log = relationship("SyncLog", back_populates="raw_products")
    
    __table_args__ = (
        Index('idx_raw_products_datasource', 'datasource_id'),
        Index('idx_raw_products_upload', 'upload_id'),
        Index('idx_raw_products_sync', 'sync_id'),
        Index('idx_raw_products_sku', 'sku'),
    )