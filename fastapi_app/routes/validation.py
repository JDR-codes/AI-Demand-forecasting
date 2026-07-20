#fastapi_app/routes/validation.py
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
from fastapi.responses import StreamingResponse
import io

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.services.validation.validation_service import (
    get_validation_errors,
    get_validation_error,
    fix_validation_error,
    ignore_validation_error,
    fix_all_validation_errors,
    ignore_all_validation_errors,
    get_validation_statistics,
    reopen_all_validation_errors,
)
from fastapi_app.schemas.validation_error_schema import (
    ValidationErrorOut,
    ValidationErrorFixRequest,
    ValidationErrorBatchFixRequest,
)
from fastapi_app.models.auth_model import User

router = APIRouter(prefix="/api/validation", tags=["Validation"])

# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard")
def get_validation_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get validation statistics for dashboard."""
    return get_validation_statistics(db)

# ============================================================================
# ERROR LISTING
# ============================================================================

@router.get("/errors", response_model=List[ValidationErrorOut])
def list_validation_errors(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get validation errors with filters and pagination."""
    offset = (page - 1) * limit
    errors = get_validation_errors(db, severity, status, source, start_date, end_date, limit, offset)
    return errors

@router.get("/errors/{error_id}", response_model=ValidationErrorOut)
def get_validation_error_endpoint(
    error_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    err = get_validation_error(db, error_id)
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err

# ============================================================================
# SINGLE ERROR OPERATIONS
# ============================================================================

@router.post("/errors/{error_id}/fix", response_model=ValidationErrorOut)
def fix_validation_error_endpoint(
    error_id: int,
    payload: ValidationErrorFixRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    err = fix_validation_error(db, error_id, payload.dict(), current_user.id)
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err

@router.post("/errors/{error_id}/ignore", response_model=ValidationErrorOut)
def ignore_validation_error_endpoint(
    error_id: int,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    err = ignore_validation_error(db, error_id, current_user.id, reason)
    if not err:
        raise HTTPException(status_code=404, detail="Validation error not found")
    return err

# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@router.post("/errors/fix-all")
def fix_all_validation_errors_endpoint(
    payload: Optional[ValidationErrorBatchFixRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fix all open validation errors."""
    source = payload.source if payload else None
    count = fix_all_validation_errors(db, current_user.id, source)
    return {"fixed_count": count, "message": f"Fixed {count} validation errors"}

@router.post("/errors/ignore-all")
def ignore_all_validation_errors_endpoint(
    payload: Optional[ValidationErrorBatchFixRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ignore all open validation errors."""
    source = payload.source if payload else None
    reason = payload.reason if payload else None
    count = ignore_all_validation_errors(db, current_user.id, source, reason)
    return {"ignored_count": count, "message": f"Ignored {count} validation errors"}

@router.post("/errors/reopen-all")
def reopen_all_validation_errors_endpoint(
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reopen all fixed/ignored validation errors."""
    count = reopen_all_validation_errors(db, source)
    return {"reopened_count": count, "message": f"Reopened {count} validation errors"}

@router.post("/errors/fix-by-severity")
def fix_errors_by_severity(
    severity: str = Query(..., pattern="^(critical|high|medium|low)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fix all validation errors of a specific severity."""
    from fastapi_app.models.validation_error_model import ValidationError
    
    count = db.query(ValidationError).filter(
        ValidationError.status == "open",
        ValidationError.severity == severity
    ).update({
        "status": "fixed",
        "is_fixed": True,
        "resolved_at": datetime.utcnow(),
        "resolved_by": current_user.id
    })
    db.commit()
    return {"fixed_count": count, "severity": severity}

@router.post("/errors/fix-by-type")
def fix_errors_by_type(
    error_type: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fix all validation errors of a specific type."""
    from fastapi_app.models.validation_error_model import ValidationError
    
    count = db.query(ValidationError).filter(
        ValidationError.status == "open",
        ValidationError.error_type == error_type
    ).update({
        "status": "fixed",
        "is_fixed": True,
        "resolved_at": datetime.utcnow(),
        "resolved_by": current_user.id
    })
    db.commit()
    return {"fixed_count": count, "error_type": error_type}

# ============================================================================
# EXPORT
# ============================================================================

@router.get("/export")
def export_validation_errors(
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export validation errors to CSV, Excel, or PDF."""
    errors = get_validation_errors(db, severity, status, source, start_date, end_date, limit=10000)
    
    data = [{
        "source": e.source,
        "error_type": e.error_type,
        "severity": e.severity,
        "rows_affected": e.rows_affected,
        "status": e.status,
        "column_name": e.column_name,
        "row_number": e.row_number,
        "expected_value": e.expected_value,
        "actual_value": e.actual_value,
        "error_message": e.error_message,
        "suggestion": e.suggestion,
        "created_at": e.created_at.isoformat() if e.created_at else None
    } for e in errors]
    
    if format == "csv":
        df = pd.DataFrame(data)
        csv_data = df.to_csv(index=False)
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=validation_errors.csv"}
        )
    elif format == "excel":
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Validation Errors', index=False)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=validation_errors.xlsx"}
        )
    else:
        # PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("Validation Errors Report", styles['Title']))
        story.append(Spacer(1, 12))
        
        if data:
            headers = list(data[0].keys())
            table_data = [headers]
            for row in data:
                table_data.append([str(row.get(h, '')) for h in headers])
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No validation errors found.", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=validation_errors.pdf"}
        )