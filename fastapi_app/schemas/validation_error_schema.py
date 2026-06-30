from pydantic import BaseModel
from typing import Optional


class ValidationErrorOut(BaseModel):
    id: int
    source: str
    error_type: str
    severity: str
    rows_affected: int
    status: str

    class Config:
        from_attributes = True


class ValidationErrorFixRequest(BaseModel):
    fix_type: str
    comments: Optional[str] = None
