#fastapi_app/schemas/audit_log_schema.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AuditLogOut(BaseModel):
    """Full audit log response."""
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    event_type: str
    success: bool
    action: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""
    items: List[AuditLogOut]
    total: int
    skip: int
    limit: int


class AuditLogExportItem(BaseModel):
    """Audit log export format."""
    id: int
    timestamp: datetime
    user_email: Optional[str]
    user_role: Optional[str]
    event_type: str
    status: str  # "Success" or "Failed"
    action: Optional[str]
    target_type: Optional[str]
    target_name: Optional[str]
    ip_address: Optional[str]
    detail: Optional[str]

    @classmethod
    def from_orm(cls, log):
        return cls(
            id=log.id,
            timestamp=log.created_at,
            user_email=log.user_email,
            user_role=log.user_role,
            event_type=log.event_type,
            status="Success" if log.success else "Failed",
            action=log.action,
            target_type=log.target_type,
            target_name=log.target_name,
            ip_address=log.ip_address,
            detail=log.detail,
        )

    class Config:
        from_attributes = True