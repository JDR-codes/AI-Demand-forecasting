from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from fastapi_app.models.alert_model import AlertSeverity, AlertCategory


class AlertCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    severity: AlertSeverity = Field(AlertSeverity.INFO)
    category: AlertCategory = Field(AlertCategory.SYSTEM)
    sku: Optional[str] = Field(None, max_length=100)
    warehouse: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)

    class Config:
        use_enum_values = True


class AlertResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: AlertSeverity
    category: AlertCategory
    sku: Optional[str]
    warehouse: Optional[str]
    region: Optional[str]
    is_read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class AlertListResponse(BaseModel):
    total: int
    unread: int
    items: List[AlertResponse]


class AlertReadResponse(BaseModel):
    id: int
    is_read: bool
    message: str


class AlertDeleteResponse(BaseModel):
    id: int
    message: str