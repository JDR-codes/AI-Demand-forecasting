# fastapi_app/models/model_registry_model.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Float, Integer, ForeignKey, Text, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    model_type = Column(String(50), nullable=False)
    
    # Versioning
    version = Column(String(50), nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    owner = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Training info
    last_trained = Column(DateTime, nullable=True)
    training_dataset = Column(String(255), nullable=True)
    training_size = Column(Integer, nullable=True)
    
    # ✅ Extended metrics for Figma model cards
    best_accuracy = Column(Float, nullable=True)
    best_rmse = Column(Float, nullable=True)
    best_mae = Column(Float, nullable=True)
    best_mape = Column(Float, nullable=True)
    best_r2 = Column(Float, nullable=True)
    best_loss = Column(Float, nullable=True)
    
    # Model metadata
    framework = Column(String(50), nullable=True)
    algorithm = Column(String(100), nullable=True)
    hyperparameters = Column(JSON, nullable=True)
    feature_set = Column(JSON, nullable=True)
    
    # Storage
    artifact_path = Column(String(1024), nullable=True)
    artifact_size = Column(Integer, nullable=True)  # Size in bytes
    training_duration = Column(Float, nullable=True)  # Seconds
    framework_version = Column(String(50), nullable=True)
    python_version = Column(String(50), nullable=True)
    git_commit = Column(String(40), nullable=True)
    dataset_hash = Column(String(64), nullable=True)
    
    meta_info = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default="active")  # active, archived, deleted
    description = Column(Text, nullable=True)
    
    # ✅ Favorite / Star (Figma card)
    is_favorite = Column(Boolean, default=False)
    
    # ✅ Deployment status (Figma card)
    deployment_status = Column(String(50), default="development")  # development, staging, production
    
    # ✅ Archived date (Figma card)
    archived_at = Column(DateTime, nullable=True)
    
    # ✅ Production version tracking (Figma card)
    production_version = Column(String(50), nullable=True)
    production_deployed_at = Column(DateTime, nullable=True)
    
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    training_jobs = relationship("TrainingJob", back_populates="model_registry")
    training_history = relationship("TrainingHistory", back_populates="model_registry")
    forecast_jobs = relationship("ForecastJob", back_populates="model_registry")
    training_config = relationship("TrainingConfiguration", back_populates="model_registry")
    forecast_config = relationship("ForecastConfiguration", back_populates="model_registry", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_model_registry_model_type', 'model_type'),
        Index('idx_model_registry_is_active', 'is_active'),
        Index('idx_model_registry_is_default', 'is_default'),
        Index('idx_model_registry_status', 'status'),
        Index('idx_model_registry_best_accuracy', 'best_accuracy'),
        Index('idx_model_registry_is_favorite', 'is_favorite'),
        Index('idx_model_registry_deployment_status', 'deployment_status'),
    )
    
    def __repr__(self):
        return f"<ModelRegistry(id={self.id}, name={self.name}, version={self.version})>"