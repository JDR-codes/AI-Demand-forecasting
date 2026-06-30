from typing import List
from sqlalchemy.orm import Session
from fastapi_app.models.validation_error_model import ValidationError


def get_validation_errors(db: Session) -> List[ValidationError]:
    return db.query(ValidationError).all()


def get_validation_error(db: Session, error_id: int) -> ValidationError | None:
    return db.query(ValidationError).filter(ValidationError.id == error_id).first()


def create_validation_error(
    db: Session,
    source: str,
    error_type: str,
    severity: str = "medium",
    rows_affected: int = 0,
    status: str = "open",
) -> ValidationError:
    err = ValidationError(
        source=source,
        error_type=error_type,
        severity=severity,
        rows_affected=rows_affected,
        status=status,
    )
    db.add(err)
    db.commit()
    db.refresh(err)
    return err


def fix_validation_error(db: Session, error_id: int, fix_request: dict) -> ValidationError | None:
    err = get_validation_error(db, error_id)
    if not err:
        return None
    err.status = "fixed"
    db.commit()
    db.refresh(err)
    return err


def ignore_validation_error(db: Session, error_id: int) -> ValidationError | None:
    err = get_validation_error(db, error_id)
    if not err:
        return None
    err.status = "ignored"
    db.commit()
    db.refresh(err)
    return err


def fix_all_validation_errors(db: Session) -> int:
    errors = db.query(ValidationError).all()
    for err in errors:
        err.status = "fixed"
    db.commit()
    return len(errors)
