from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DataSourceBase(BaseModel):
    name: str
    type: str
    connection_string: str


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    connection_string: Optional[str] = None
    status: Optional[str] = None
    health: Optional[str] = None


class DataSourceOut(DataSourceBase):
    id: int
    status: str
    health: str
    last_sync: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
