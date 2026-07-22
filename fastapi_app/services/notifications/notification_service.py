# fastapi_app/services/notifications/notification_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func, or_
from datetime import datetime
import asyncio

from fastapi_app.models.notification_model import (
    Notification,
    NotificationStatus,
    NotificationType,
    NotificationPriority
)
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.notification_schema import NotificationCreate, NotificationFilter
from fastapi_app.services.websocket.websocket_manager import manager

import logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications."""
    
    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        entity_type: str = None,
        entity_id: str = None,
        send_websocket: bool = True
    ) -> Notification:
        """Create a new notification and optionally send via WebSocket."""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            priority=priority,
            entity_type=entity_type,
            entity_id=entity_id,
            status=NotificationStatus.UNREAD
        )
        db.add(notification)
        
        try:
            db.commit()
            db.refresh(notification)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create notification: {str(e)}")
            raise
        
        # Send WebSocket notification using safe event loop
        if send_websocket:
            try:
                # Get the running event loop or create a new one
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        manager.send_notification(
                            user_id=user_id,
                            title=title,
                            message=message,
                            notification_type=notification_type.value,
                            priority=priority.value
                        )
                    )
                except RuntimeError:
                    # No running loop, create a new event loop
                    asyncio.run(
                        manager.send_notification(
                            user_id=user_id,
                            title=title,
                            message=message,
                            notification_type=notification_type.value,
                            priority=priority.value
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to send WebSocket notification: {e}")
        
        return notification
    
    @staticmethod
    def broadcast_notification(
        db: Session,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        entity_type: str = None,
        entity_id: str = None,
        send_websocket: bool = True
    ) -> List[Notification]:
        """Send a notification to multiple users."""
        notifications = []
        for user_id in user_ids:
            notification = NotificationService.create_notification(
                db=db,
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                entity_type=entity_type,
                entity_id=entity_id,
                send_websocket=send_websocket
            )
            notifications.append(notification)
        return notifications
    
    @staticmethod
    def get_notifications(
        db: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[NotificationStatus] = None,
        priority: Optional[NotificationPriority] = None,
        notification_type: Optional[NotificationType] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Notification]:
        """Get notifications for a user with filters."""
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if status:
            query = query.filter(Notification.status == status)
        if priority:
            query = query.filter(Notification.priority == priority)
        if notification_type:
            query = query.filter(Notification.type == notification_type)
        if search:
            query = query.filter(
                or_(
                    Notification.title.contains(search),
                    Notification.message.contains(search)
                )
            )
        if start_date:
            query = query.filter(Notification.created_at >= start_date)
        if end_date:
            query = query.filter(Notification.created_at <= end_date)
        
        return query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        """Get unread notification count for a user."""
        return db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.status == NotificationStatus.UNREAD
        ).scalar() or 0
    
    @staticmethod
    def get_notification(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
        """Get a specific notification."""
        return db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
    
    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
        """Mark a notification as read."""
        notification = NotificationService.get_notification(db, notification_id, user_id)
        if not notification:
            return None
        
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(notification)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to mark notification as read: {str(e)}")
            raise
        
        # Send WebSocket update using safe event loop
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    manager.send_to_user(
                        user_id=user_id,
                        message={
                            "type": "notification_read",
                            "notification_id": notification_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                )
            except RuntimeError:
                asyncio.run(
                    manager.send_to_user(
                        user_id=user_id,
                        message={
                            "type": "notification_read",
                            "notification_id": notification_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                )
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification read: {e}")
        
        return notification
    
    @staticmethod
    def mark_all_read(db: Session, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status == NotificationStatus.UNREAD
        ).update({
            "status": NotificationStatus.READ,
            "read_at": datetime.utcnow()
        })
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to mark all notifications as read: {str(e)}")
            raise
        
        # Send WebSocket update using safe event loop
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    manager.send_to_user(
                        user_id=user_id,
                        message={
                            "type": "notifications_read_all",
                            "count": count,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                )
            except RuntimeError:
                asyncio.run(
                    manager.send_to_user(
                        user_id=user_id,
                        message={
                            "type": "notifications_read_all",
                            "count": count,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                )
        except Exception as e:
            logger.error(f"Failed to send WebSocket read all: {e}")
        
        return count
    
    @staticmethod
    def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
        """Archive/delete a notification."""
        notification = NotificationService.get_notification(db, notification_id, user_id)
        if not notification:
            return False
        
        notification.status = NotificationStatus.ARCHIVED
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to archive notification: {str(e)}")
            raise
        
        return True
    
    @staticmethod
    def delete_permanently(db: Session, notification_id: int, user_id: int) -> bool:
        """Permanently delete a notification."""
        notification = NotificationService.get_notification(db, notification_id, user_id)
        if not notification:
            return False
        
        db.delete(notification)
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to permanently delete notification: {str(e)}")
            raise
        
        return True
    
    # ==========================================================================
    # CONVENIENCE METHODS FOR SPECIFIC NOTIFICATIONS
    # ==========================================================================
    
    @staticmethod
    def create_forecast_notification(
        db: Session,
        user_id: int,
        job_id: str,
        success: bool,
        message: str = None
    ) -> Notification:
        """Create a notification for forecast job completion."""
        if success:
            title = f"Forecast {job_id} completed successfully"
            message = message or f"Forecast job {job_id} completed successfully."
            priority = NotificationPriority.MEDIUM
        else:
            title = f"Forecast {job_id} failed"
            message = message or f"Forecast job {job_id} failed. Please check the logs."
            priority = NotificationPriority.HIGH
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.FORECAST,
            priority=priority,
            entity_type="forecast_job",
            entity_id=job_id
        )
    
    @staticmethod
    def create_training_notification(
        db: Session,
        user_id: int,
        model_type: str,
        success: bool,
        accuracy: float = None,
        message: str = None
    ) -> Notification:
        """Create a notification for training job completion."""
        if success:
            acc_msg = f" Accuracy improved to {accuracy:.1%}." if accuracy else ""
            title = f"{model_type} retraining completed"
            message = message or f"{model_type} retraining completed successfully.{acc_msg}"
            priority = NotificationPriority.MEDIUM
        else:
            title = f"{model_type} retraining failed"
            message = message or f"{model_type} retraining failed. Please check the logs."
            priority = NotificationPriority.HIGH
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.TRAINING,
            priority=priority,
            entity_type="training_job",
            entity_id=model_type
        )
    
    @staticmethod
    def create_sync_notification(
        db: Session,
        user_id: int,
        datasource_name: str,
        success: bool,
        message: str = None
    ) -> Notification:
        """Create a notification for data source sync."""
        if success:
            title = f"Data sync completed: {datasource_name}"
            message = message or f"Data source '{datasource_name}' synced successfully."
            priority = NotificationPriority.LOW
        else:
            title = f"Data sync failed: {datasource_name}"
            message = message or f"Data source '{datasource_name}' sync failed."
            priority = NotificationPriority.HIGH
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.SYNC,
            priority=priority,
            entity_type="data_source",
            entity_id=datasource_name
        )
    
    @staticmethod
    def create_upload_notification(
        db: Session,
        user_id: int,
        filename: str,
        success: bool,
        rows: int = None,
        message: str = None
    ) -> Notification:
        """Create a notification for upload completion."""
        if success:
            rows_msg = f" {rows} records stored." if rows else ""
            title = f"Upload completed: {filename}"
            message = message or f"Upload '{filename}' processed successfully.{rows_msg}"
            priority = NotificationPriority.LOW
        else:
            title = f"Upload failed: {filename}"
            message = message or f"Upload '{filename}' failed. Please check the logs."
            priority = NotificationPriority.HIGH
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.UPLOAD,
            priority=priority,
            entity_type="upload",
            entity_id=filename
        )
    
    @staticmethod
    def create_processing_notification(
        db: Session,
        user_id: int,
        job_id: str,
        success: bool,
        message: str = None
    ) -> Notification:
        """Create a notification for processing job completion."""
        if success:
            title = f"Processing job {job_id} completed"
            message = message or f"Processing job {job_id} completed successfully."
            priority = NotificationPriority.MEDIUM
        else:
            title = f"Processing job {job_id} failed"
            message = message or f"Processing job {job_id} failed. Please check the logs."
            priority = NotificationPriority.HIGH
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.PROCESSING,
            priority=priority,
            entity_type="processing_job",
            entity_id=job_id
        )
    
    @staticmethod
    def create_validation_notification(
        db: Session,
        user_id: int,
        source: str,
        errors: int,
        message: str = None
    ) -> Notification:
        """Create a notification for validation issues."""
        title = f"Validation errors found in {source}"
        message = message or f"{errors} validation errors found in {source}."
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.VALIDATION,
            priority=NotificationPriority.HIGH if errors > 10 else NotificationPriority.MEDIUM,
            entity_type="validation",
            entity_id=source
        )
    
    @staticmethod
    def create_alert_notification(
        db: Session,
        user_id: int,
        alert_title: str,
        alert_message: str,
        priority: NotificationPriority = NotificationPriority.HIGH
    ) -> Notification:
        """Create a notification for system alerts."""
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=f"Alert: {alert_title}",
            message=alert_message,
            notification_type=NotificationType.ALERT,
            priority=priority,
            entity_type="alert"
        )
    
    @staticmethod
    def create_system_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> Notification:
        """Create a system notification."""
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.SYSTEM,
            priority=priority
        )
        
    @staticmethod
    def create_recommendation_notification(
        db: Session,
        user_id: int,
        job_id: str = None,
        success: bool = True,
        count: int = 0,
        message: str = None
    ) -> Optional[Notification]:
        """Create recommendation notification."""
        if not user_id:
            return None
        
        if success:
            title = f"✅ Recommendation Job Completed"
            default_msg = f"Generated {count} recommendations"
        else:
            title = f"❌ Recommendation Job Failed"
            default_msg = f"Recommendation job failed: {message or 'Unknown error'}"
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message or default_msg,
            notification_type="recommendation",
            priority="info" if success else "critical"
        )

    @staticmethod
    def create_critical_recommendation_notification(
        db: Session,
        user_id: int,
        recommendation: Dict[str, Any]
    ) -> Optional[Notification]:
        """Create critical recommendation notification."""
        if not user_id:
            return None
        
        sku = recommendation.get("sku", "Unknown")
        action = recommendation.get("action_label", "Take action")
        
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=f"🚨 CRITICAL RECOMMENDATION - SKU {sku}",
            message=f"Critical action required: {action}",
            notification_type="recommendation_critical",
            priority="critical"
        )
