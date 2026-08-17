# fastapi_app/models/data_source_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, Text, BigInteger, Index, Boolean, ForeignKey
from fastapi_app.db.session import Base
import enum
from sqlalchemy.orm import relationship


class DataSourceType(str, enum.Enum):
    API = "API"
    DATABASE = "DATABASE"
    CLOUD_STORAGE = "CLOUD_STORAGE"
    LOCAL_FOLDER = "LOCAL_FOLDER"


class DataSourceProvider(str, enum.Enum):
    # PURELY CONNECTION/PROVIDER TYPES - NOT DATA CATEGORIES
    SAP = "SAP"
    MYSQL = "MYSQL"
    POSTGRES = "POSTGRES"
    SQLITE = "SQLITE"
    S3 = "S3"
    MINIO = "MINIO"
    CUSTOM = "CUSTOM"


class DataCategory(str, enum.Enum):
    SALES = "sales"
    INVENTORY = "inventory"
    SUPPLIER = "supplier"
    PRODUCTS = "products"


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(DataSourceType), nullable=False)
    provider = Column(Enum(DataSourceProvider), nullable=True)
    
    # Data category - what kind of data this source provides
    data_category = Column(String(50), nullable=False, default="sales")
    
    base_url = Column(String(1024), nullable=True)
    connection_string = Column(String(1024), nullable=True)
    api_key = Column(String(512), nullable=True)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    bucket_name = Column(String(255), nullable=True)
    folder_path = Column(String(1024), nullable=True)
    table_name = Column(String(255), nullable=True)
    
    # Ownership metadata for user/company enforcement during input selection and scheduling
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Enabled state - separate from sync status
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Status represents current operational/sync state: idle, syncing, success, partial_success, failed
    status = Column(String(50), default="idle", nullable=False)
    health = Column(String(50), default="unknown", nullable=False)
    sync_frequency = Column(String(50), default="manual", nullable=False)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Dashboard fields (denormalized)
    record_count = Column(BigInteger, default=0)
    health_score = Column(Float, default=100.0)
    last_sync_duration = Column(Float, nullable=True)
    next_sync = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    sync_logs = relationship(
        "SyncLog",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )
    sync_jobs = relationship(
        "SyncJob",
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
    validation_errors = relationship(
        "ValidationError",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )
    connection_history = relationship(
        "ConnectionHistory",
        back_populates="datasource",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_datasource_status', 'status'),
        Index('idx_datasource_type', 'type'),
        Index('idx_datasource_created_at', 'created_at'),
        Index('idx_datasource_sync_frequency', 'sync_frequency'),
        Index('idx_datasource_health', 'health'),
        Index('idx_datasource_health_score', 'health_score'),
        Index('idx_datasource_is_enabled', 'is_enabled'),
        Index('idx_datasource_data_category', 'data_category'),
    )

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, type={self.type}, status={self.status})>"