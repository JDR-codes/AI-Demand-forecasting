#fastapi_app/models/notification_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship
import enum


class NotificationStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, enum.Enum):
    FORECAST = "forecast"
    TRAINING = "training"
    ALERT = "alert"
    INVENTORY = "inventory"
    SYSTEM = "system"
    SYNC = "sync"
    UPLOAD = "upload"
    PROCESSING = "processing"
    VALIDATION = "validation"


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.UNREAD)
    
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(36), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_notification_user_id', 'user_id'),
        Index('idx_notification_status', 'status'),
        Index('idx_notification_type', 'type'),
        Index('idx_notification_created_at', 'created_at'),
        Index('idx_notification_entity', 'entity_type', 'entity_id'),
    )
    
    def __repr__(self):
        return f"<Notification(id={self.id}, title={self.title}, status={self.status})>"