from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ScenarioBase(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class ScenarioResponse(ScenarioBase):
    id: int
    status: str
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_output: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
