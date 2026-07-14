# fastapi_app/models/data_source_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum
from fastapi_app.db.session import Base
import enum
from sqlalchemy.orm import relationship

class DataSourceType(str, enum.Enum):
    API = "API"
    DATABASE = "DATABASE"
    CLOUD_STORAGE = "CLOUD_STORAGE"
    LOCAL_FOLDER = "LOCAL_FOLDER"

class DataSourceProvider(str, enum.Enum):
    SAP = "SAP"
    MYSQL = "MYSQL"
    POSTGRES = "POSTGRES"
    SQLITE = "SQLITE"
    S3 = "S3"
    MINIO = "MINIO"
    SUPPLIER = "SUPPLIER"
    SALES = "SALES"
    INVENTORY = "INVENTORY"
    WEATHER = "WEATHER"
    CUSTOM = "CUSTOM"

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(DataSourceType), nullable=False)
    provider = Column(Enum(DataSourceProvider), nullable=True)
    base_url = Column(String(1024), nullable=True)
    connection_string = Column(String(1024), nullable=True)
    api_key = Column(String(512), nullable=True)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    bucket_name = Column(String(255), nullable=True)
    folder_path = Column(String(1024), nullable=True)
    table_name = Column(String(255), nullable=True)
    
    status = Column(String(50), default="inactive", nullable=False)
    health = Column(String(50), default="unknown", nullable=False)
    sync_frequency = Column(String(50), default="manual", nullable=False)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships with proper back_populates and cascade
    sync_logs = relationship(
        "SyncLog",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )
    raw_sales = relationship(
        "RawSales",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )
    raw_inventory = relationship(
        "RawInventory",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )
    raw_suppliers = relationship(
        "RawSupplier",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )
    raw_products = relationship(
        "RawProducts",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, type={self.type}, status={self.status})>"