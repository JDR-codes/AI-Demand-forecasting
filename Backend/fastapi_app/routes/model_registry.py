#fastapi_app/routes/model_registry.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user, require_permission_dep
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.forecast_schema import ModelRegistryResponse
from fastapi_app.services.forecast.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/api/forecast/models", tags=["Forecast Models"])


@router.get("/", response_model=List[ModelRegistryResponse])
def list_models(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
):
    """List all registered forecast models with metrics."""
    return ModelRegistryService.get_models(db, active_only)


@router.get("/{model_id}", response_model=ModelRegistryResponse)
def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:read"))
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
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Update model status (activate/deactivate)."""
    if is_active:
        if not ModelRegistryService.activate_model(db, model_id):
            raise HTTPException(status_code=404, detail="Model not found")
    else:
        if not ModelRegistryService.deactivate_model(db, model_id):
            raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model updated successfully"}


@router.delete("/{model_id}")
def delete_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:delete"))
):
    """Delete a registered model."""
    if not ModelRegistryService.delete_model(db, model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}


@router.post("/{model_id}/promote")
def promote_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Promote a model version to be default/active."""
    if not ModelRegistryService.promote_model(db, model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model promoted to default successfully"}


@router.post("/{model_id}/favorite")
def toggle_favorite(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Toggle favorite status of a model card."""
    model = ModelRegistryService.toggle_favorite(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Favorite toggled", "is_favorite": model.is_favorite}


@router.post("/{model_id}/deploy")
def deploy_model(
    model_id: str,
    status: str = Query(..., enum=["development", "staging", "production"]),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Deploy model to staging or production."""
    model = ModelRegistryService.update_deployment(db, model_id, status)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "message": f"Model deployed to {status}",
        "deployment_status": model.deployment_status
    }


@router.post("/{model_id}/restore")
def restore_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_dep("forecast:run"))
):
    """Restore an archived model."""
    if not ModelRegistryService.restore_model(db, model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model restored successfully"}