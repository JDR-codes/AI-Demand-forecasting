#fastapi_app/routes/training_config.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.training_config_schema import (
    TrainingConfigCreate,
    TrainingConfigUpdate,
    TrainingConfigResponse
)
from fastapi_app.services.forecast.training_config_service import TrainingConfigService

router = APIRouter(prefix="/api/training/configurations", tags=["Training Configurations"])


@router.get("/", response_model=List[TrainingConfigResponse])
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all training configurations."""
    return TrainingConfigService.get_configs(db)


@router.get("/{config_id}", response_model=TrainingConfigResponse)
def get_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific configuration."""
    config = TrainingConfigService.get_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.post("/", response_model=TrainingConfigResponse)
def create_config(
    config: TrainingConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new training configuration."""
    return TrainingConfigService.create_config(db, config)


@router.put("/{config_id}", response_model=TrainingConfigResponse)
def update_config(
    config_id: int,
    config_update: TrainingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a training configuration."""
    config = TrainingConfigService.update_config(db, config_id, config_update)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.patch("/{config_id}/toggle")
def toggle_config(
    config_id: int,
    enabled: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enable or disable a configuration."""
    config = TrainingConfigService.toggle_config(db, config_id, enabled)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": f"Configuration {'enabled' if enabled else 'disabled'}"}