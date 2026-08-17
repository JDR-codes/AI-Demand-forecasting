#fastapi_app/routes/notifications.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.notification_model import Notification, NotificationStatus, NotificationPriority, NotificationType
from fastapi_app.schemas.notification_schema import (
    NotificationResponse,
    NotificationListResponse,
    NotificationCountResponse,
    NotificationStatusUpdateResponse
)
from fastapi_app.services.notifications.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    notification_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notifications with filters."""
    try:
        status_enum = NotificationStatus(status) if status else None
    except ValueError:
        status_enum = None
    
    try:
        priority_enum = NotificationPriority(priority) if priority else None
    except ValueError:
        priority_enum = None
    
    try:
        type_enum = NotificationType(notification_type) if notification_type else None
    except ValueError:
        type_enum = None
    
    return NotificationService.get_notifications(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status_enum,
        priority=priority_enum,
        notification_type=type_enum,
        search=search
    )


@router.get("/list", response_model=NotificationListResponse)
def get_notifications_paginated(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    notification_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notifications with pagination."""
    try:
        status_enum = NotificationStatus(status) if status else None
    except ValueError:
        status_enum = None
    
    try:
        priority_enum = NotificationPriority(priority) if priority else None
    except ValueError:
        priority_enum = None
    
    try:
        type_enum = NotificationType(notification_type) if notification_type else None
    except ValueError:
        type_enum = None
    
    offset = (page - 1) * limit
    items = NotificationService.get_notifications(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status_enum,
        priority=priority_enum,
        notification_type=type_enum,
        search=search
    )
    
    total = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).count()
    
    unread_count = NotificationService.get_unread_count(db, current_user.id)
    
    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/unread", response_model=NotificationCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get unread notification count."""
    count = NotificationService.get_unread_count(db, current_user.id)
    return NotificationCountResponse(unread_count=count)


@router.patch("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read."""
    count = NotificationService.mark_all_read(db, current_user.id)
    return {"message": f"{count} notifications marked as read", "count": count}


@router.patch("/{notification_id}", response_model=NotificationStatusUpdateResponse)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read."""
    notification = NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationStatusUpdateResponse(
        id=notification.id,
        status=notification.status,
        message="Notification marked as read"
    )


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete/archive a notification."""
    if not NotificationService.delete_notification(db, notification_id, current_user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}


@router.delete("/{notification_id}/permanent")
def delete_notification_permanently(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permanently delete a notification."""
    if not NotificationService.delete_permanently(db, notification_id, current_user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification permanently deleted"}