# fastapi_app/models/raw_data_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Text
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship

class RawSales(Base):
    __tablename__ = "raw_sales"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
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
    
    # Relationships with proper back_populates
    datasource = relationship("DataSource", back_populates="raw_sales")
    sync_log = relationship("SyncLog", back_populates="raw_sales")

class RawInventory(Base):
    __tablename__ = "raw_inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
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
    sync_log = relationship("SyncLog", back_populates="raw_inventory")

class RawSupplier(Base):
    __tablename__ = "raw_suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
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
    sync_log = relationship("SyncLog", back_populates="raw_suppliers")

class RawProducts(Base):
    __tablename__ = "raw_products"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
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
    sync_log = relationship("SyncLog", back_populates="raw_products")