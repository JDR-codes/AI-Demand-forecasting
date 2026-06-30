from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UploadOut(BaseModel):
    id: int
    filename: str
    file_path: str
    status: str
    uploaded_by: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
