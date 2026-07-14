# fastapi_app/schemas/data_source_schema.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class DataSourceType(str, Enum):
    API = "API"
    DATABASE = "DATABASE"
    CLOUD_STORAGE = "CLOUD_STORAGE"
    LOCAL_FOLDER = "LOCAL_FOLDER"

class DataSourceProvider(str, Enum):
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

class DataSourceBase(BaseModel):
    name: str
    type: DataSourceType
    provider: Optional[DataSourceProvider] = None
    base_url: Optional[str] = None
    connection_string: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    bucket_name: Optional[str] = None
    folder_path: Optional[str] = None
    table_name: Optional[str] = None  # ✅ Added
    sync_frequency: Optional[str] = "manual"

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[DataSourceType] = None
    provider: Optional[DataSourceProvider] = None
    base_url: Optional[str] = None
    connection_string: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    bucket_name: Optional[str] = None
    folder_path: Optional[str] = None
    table_name: Optional[str] = None  # ✅ Added
    status: Optional[str] = None
    health: Optional[str] = None
    sync_frequency: Optional[str] = None

class DataSourceOut(DataSourceBase):
    id: int
    status: str
    health: str
    last_sync: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True