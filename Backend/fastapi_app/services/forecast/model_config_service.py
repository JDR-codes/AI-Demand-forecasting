# fastapi_app/services/forecast/model_config_service.py
"""
Model Config Service - Handles model configuration for Figma popup.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.models.forecast_configuration_model import ForecastConfiguration
from fastapi_app.schemas.forecast_schema import ModelConfigResponse, ModelConfigUpdate
from fastapi_app.services.forecast.model_registry_service import ModelRegistryService


class ModelConfigService:
    """Service for model configuration management."""
    
    @staticmethod
    def get_model_config(db: Session, model_id: str) -> Optional[Dict[str, Any]]:
        """Get full configuration for a model."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return None
        
        # Get forecast config
        config = db.query(ForecastConfiguration).filter(
            ForecastConfiguration.model_registry_id == model_id
        ).first()
        
        # Build response
        response = {
            "id": model.id,
            "name": model.name,
            "model_type": model.model_type,
            "forecast_horizon": config.forecast_horizon if config else 30,
            "seasonality": config.seasonality if config else True,
            "validation_split": 0.2,  # Segregated retraining parameter
            "default_dataset": config.default_dataset if config else "Latest Processed Data",
            "default_region": config.default_region if config else None,
            "default_sku": config.default_sku if config else None,
            "default_warehouse": config.default_warehouse if config else None,
            "epochs": 100,  # Segregated retraining parameter
            "batch_size": 16,  # Segregated retraining parameter
            "learning_rate": 0.001,  # Segregated retraining parameter
            "is_default": model.is_default,
            "last_trained": model.last_trained.isoformat() if model.last_trained else None,
            "accuracy": model.best_accuracy,
            "dataset_size": model.training_size,
            "date_range": {
                "start": (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "last_updated": model.updated_at.isoformat() if model.updated_at else None
        }
        
        return response
    
    @staticmethod
    def update_model_config(
        db: Session,
        model_id: str,
        update: ModelConfigUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update model configuration."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return None
        
        # Get or create forecast config
        config = db.query(ForecastConfiguration).filter(
            ForecastConfiguration.model_registry_id == model_id
        ).first()
        
        if not config:
            config = ForecastConfiguration(
                model_registry_id=model_id,
                forecast_horizon=30,
                seasonality=True,
                default_dataset="Latest Processed Data"
            )
            db.add(config)
        
        # Update config fields that exist on ForecastConfiguration
        update_data = update.dict(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(config)
        db.refresh(model)
        
        return ModelConfigService.get_model_config(db, model_id)