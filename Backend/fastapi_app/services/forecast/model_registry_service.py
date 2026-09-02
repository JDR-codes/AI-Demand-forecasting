#fastapi_app/services/forecast/model_registry_service.py

"""
Model Registry Service - Single source of truth for ModelRegistry operations.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.models.training_job_model import TrainingHistory
from fastapi_app.schemas.forecast_schema import ModelRegistryCreate


class ModelRegistryService:
    """Single service for all ModelRegistry operations."""
    
    @staticmethod
    def get_models(db: Session, active_only: bool = True) -> List[ModelRegistry]:
        """Get all registered models."""
        query = db.query(ModelRegistry)
        if active_only:
            query = query.filter(ModelRegistry.is_active == True)
        return query.order_by(desc(ModelRegistry.created_at)).all()
    
    @staticmethod
    def get_model(db: Session, model_id: str) -> Optional[ModelRegistry]:
        """Get a specific model by ID."""
        return db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
    
    @staticmethod
    def get_default_model(db: Session) -> Optional[ModelRegistry]:
        """Get the default model."""
        return db.query(ModelRegistry).filter(
            ModelRegistry.is_default == True,
            ModelRegistry.is_active == True
        ).first()
    
    @staticmethod
    def create_model(
        db: Session,
        config: ModelRegistryCreate,
        owner_id: int = None
    ) -> ModelRegistry:
        """Create a new model registry entry."""
        model = ModelRegistry(
            name=config.name,
            model_type=config.model_type,
            version=config.version,
            description=config.description,
            hyperparameters=config.hyperparameters,
            is_default=config.is_default,
            owner=owner_id,
            status="active"
        )
        
        if config.is_default:
            db.query(ModelRegistry).filter(
                ModelRegistry.is_default == True
            ).update({"is_default": False})
        
        db.add(model)
        db.commit()
        db.refresh(model)
        return model
    
    @staticmethod
    def create_model_from_training(
        db: Session,
        name: str,
        model_type: str,
        artifact_path: str = None,
        training_size: int = None,
        hyperparameters: dict = None,
        version: str = "1.0.0",
        framework: str = None,
        algorithm: str = None
    ) -> ModelRegistry:
        """Create a model from training results."""
        model = ModelRegistry(
            name=name,
            model_type=model_type,
            version=version,
            artifact_path=artifact_path,
            last_trained=datetime.utcnow(),
            training_size=training_size,
            hyperparameters=hyperparameters or {},
            framework=framework,
            algorithm=algorithm,
            status="active",
            is_active=True
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model
    
    @staticmethod
    def update_model(
        db: Session,
        model_id: str,
        **kwargs
    ) -> Optional[ModelRegistry]:
        """Update a model."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return None
        
        for key, value in kwargs.items():
            if hasattr(model, key) and value is not None:
                setattr(model, key, value)
        
        db.commit()
        db.refresh(model)
        return model
    
    @staticmethod
    def activate_model(db: Session, model_id: str) -> bool:
        """Activate a model."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return False
        model.is_active = True
        db.commit()
        return True
    
    @staticmethod
    def deactivate_model(db: Session, model_id: str) -> bool:
        """Deactivate a model (soft delete)."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return False
        # ✅ Soft delete - mark as inactive instead of deleting
        model.is_active = False
        model.status = "archived"
        db.commit()
        return True
    
    @staticmethod
    def delete_model(db: Session, model_id: str) -> bool:
        """Delete a model (hard delete - use with caution)."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return False
        # ✅ Mark as deleted instead of hard delete for safety
        model.status = "deleted"
        model.is_active = False
        db.commit()
        return True
    
    @staticmethod
    def promote_model(db: Session, model_id: str) -> bool:
        """Promote a model to be the default forecasting model."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return False
        # De-promote all other models
        db.query(ModelRegistry).update({"is_default": False})
        # Promote this model
        model.is_default = True
        model.is_active = True
        model.status = "active"
        db.commit()
        return True
    
    @staticmethod
    def record_training_history(
        db: Session,
        **kwargs
    ) -> TrainingHistory:
        """Record training history for a model."""
        if "status" not in kwargs:
            kwargs["status"] = "completed"
        history = TrainingHistory(**kwargs)
        db.add(history)
        db.commit()
        db.refresh(history)
        return history

    @staticmethod
    def get_training_history(
        db: Session,
        model_registry_id: str = None,
        limit: int = 50
    ) -> List[TrainingHistory]:
        """Get training history for a model or all models."""
        query = db.query(TrainingHistory)
        if model_registry_id:
            query = query.filter(TrainingHistory.model_registry_id == model_registry_id)
        return query.order_by(desc(TrainingHistory.trained_at)).limit(limit).all()

    @staticmethod
    def toggle_favorite(db: Session, model_id: str) -> Optional[ModelRegistry]:
        """Toggle favorite state of a model."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return None
        model.is_favorite = not model.is_favorite
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def update_deployment(db: Session, model_id: str, status: str) -> Optional[ModelRegistry]:
        """Update model deployment status (development, staging, production)."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return None
        model.deployment_status = status
        if status == "production":
            model.production_version = model.version
            model.production_deployed_at = datetime.utcnow()
            # Demote any other model of the same type in production
            db.query(ModelRegistry).filter(
                ModelRegistry.id != model_id,
                ModelRegistry.model_type == model.model_type,
                ModelRegistry.deployment_status == "production"
            ).update({"deployment_status": "staging"})
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def restore_model(db: Session, model_id: str) -> bool:
        """Restore an archived model."""
        model = ModelRegistryService.get_model(db, model_id)
        if not model:
            return False
        model.is_active = True
        model.status = "active"
        db.commit()
        return True