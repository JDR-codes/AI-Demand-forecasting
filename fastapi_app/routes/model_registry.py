#fastapi_app/routes/model_registry.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import ModelRegistryResponse
from fastapi_app.services.forecast.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/api/forecast/models", tags=["Forecast Models"])


@router.get("/", response_model=List[ModelRegistryResponse])
def list_models(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all registered forecast models with metrics."""
    return ModelRegistryService.get_models(db, active_only)


@router.get("/{model_id}", response_model=ModelRegistryResponse)
def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific model with full metrics."""
    model = ModelRegistryService.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/{model_id}")
def update_model(
    model_id: str,
    is_active: bool = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update model status (activate/deactivate)."""
    if is_active:
        if not ModelRegistryService.activate_model(db, model_id):
            raise HTTPException(status_code=404, detail="Model not found")
    else:
        if not ModelRegistryService.deactivate_model(db, model_id):
            raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model updated successfully"}