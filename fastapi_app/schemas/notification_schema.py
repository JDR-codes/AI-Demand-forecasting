#fastapi_app/schemas/notification_schema.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class NotificationType(str, Enum):
    FORECAST = "forecast"
    TRAINING = "training"
    ALERT = "alert"
    INVENTORY = "inventory"
    SYSTEM = "system"
    SYNC = "sync"
    UPLOAD = "upload"
    PROCESSING = "processing"
    VALIDATION = "validation"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class NotificationCreate(BaseModel):
    """Schema for creating a new notification."""
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


class NotificationUpdate(BaseModel):
    """Schema for updating a notification."""
    status: Optional[NotificationStatus] = None


class NotificationFilter(BaseModel):
    """Schema for filtering notifications."""
    status: Optional[NotificationStatus] = None
    priority: Optional[NotificationPriority] = None
    notification_type: Optional[NotificationType] = None
    search: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: int
    user_id: int
    title: str
    message: str
    type: NotificationType
    priority: NotificationPriority
    status: NotificationStatus
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list."""
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    limit: int
    pages: int


class NotificationCountResponse(BaseModel):
    """Schema for unread count response."""
    unread_count: int


class NotificationStatusUpdateResponse(BaseModel):
    """Schema for status update response."""
    id: int
    status: NotificationStatus
    message: str

    class Config:
        from_attributes = True


# ============================================================================
# WEBSOCKET NOTIFICATION SCHEMAS
# ============================================================================

class WebSocketNotification(BaseModel):
    """Schema for WebSocket notification message."""
    type: str = "notification"
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WebSocketNotificationRead(BaseModel):
    """Schema for WebSocket read notification message."""
    type: str = "notification_read"
    notification_id: int
    user_id: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())