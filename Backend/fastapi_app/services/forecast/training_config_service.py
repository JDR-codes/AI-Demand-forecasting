#fastapi_app/services/forecast/training_config_service.py

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from fastapi_app.models.training_configuration_model import TrainingConfiguration
from fastapi_app.schemas.training_config_schema import TrainingConfigCreate, TrainingConfigUpdate


class TrainingConfigService:
    """Service for managing training configurations."""
    
    @staticmethod
    def get_configs(db: Session) -> List[TrainingConfiguration]:
        """Get all training configurations."""
        return db.query(TrainingConfiguration).order_by(desc(TrainingConfiguration.created_at)).all()
    
    @staticmethod
    def get_config(db: Session, config_id: int) -> Optional[TrainingConfiguration]:
        """Get a specific configuration."""
        return db.query(TrainingConfiguration).filter(TrainingConfiguration.id == config_id).first()
    
    @staticmethod
    def get_config_by_model(db: Session, model_registry_id: str) -> Optional[TrainingConfiguration]:
        """Get configuration for a specific model."""
        return db.query(TrainingConfiguration).filter(
            TrainingConfiguration.model_registry_id == model_registry_id
        ).first()
    
    @staticmethod
    def create_config(
        db: Session,
        config: TrainingConfigCreate
    ) -> TrainingConfiguration:
        """Create a new training configuration."""
        db_config = TrainingConfiguration(**config.dict())
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return db_config
    
    @staticmethod
    def update_config(
        db: Session,
        config_id: int,
        config_update: TrainingConfigUpdate
    ) -> Optional[TrainingConfiguration]:
        """Update a training configuration."""
        db_config = TrainingConfigService.get_config(db, config_id)
        if not db_config:
            return None
        
        update_data = config_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_config, key, value)
        
        db_config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_config)
        return db_config
    
    @staticmethod
    def toggle_config(db: Session, config_id: int, enabled: bool) -> Optional[TrainingConfiguration]:
        """Enable or disable a configuration."""
        db_config = TrainingConfigService.get_config(db, config_id)
        if not db_config:
            return None
        db_config.enabled = enabled
        db_config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_config)
        return db_config