from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UploadOut(BaseModel):
    id: int

    filename: str

    unique_filename: str

    file_path: str

    file_url: str

    status: str

    uploaded_by: Optional[int] = None

    uploaded_at: datetime

    class Config:
        from_attributes = True
