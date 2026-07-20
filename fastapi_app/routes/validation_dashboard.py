#fastapi_app/routes/validation_dashboard.py
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.models.validation_error_model import ValidationError

router = APIRouter(prefix="/api/validation/dashboard", tags=["Validation Dashboard"])


@router.get("/")
def get_validation_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation statistics."""
    
    # Count by status
    open_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "open"
    ).scalar() or 0
    
    fixed_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "fixed"
    ).scalar() or 0
    
    ignored_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "ignored"
    ).scalar() or 0
    
    # Count by severity
    error_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.severity == "high"
    ).scalar() or 0
    
    warning_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.severity == "medium"
    ).scalar() or 0
    
    info_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.severity == "low"
    ).scalar() or 0
    
    total = db.query(func.count(ValidationError.id)).scalar() or 0
    
    return {
        "total": total,
        "open": open_count,
        "fixed": fixed_count,
        "ignored": ignored_count,
        "by_severity": {
            "error": error_count,
            "warning": warning_count,
            "info": info_count
        },
        "resolution_rate": round((fixed_count / total) * 100 if total > 0 else 0, 1),
        "timestamp": datetime.utcnow().isoformat()
    }