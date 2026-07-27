# fastapi_app/models/__init__.py
"""
Models package - import all models here for easy access.
All models are registered with Base.metadata when imported.
"""

# ============================================================================
# ALERT MODELS
# ============================================================================
from fastapi_app.models.alert_model import Alert

# ============================================================================
# AUTH MODELS
# ============================================================================
from fastapi_app.models.auth_model import User
from fastapi_app.models.auth_audit_log_model import AuthAuditLog
from fastapi_app.models.otp_model import OtpRecord
from fastapi_app.models.permission_model import Permission
from fastapi_app.models.refresh_token_model import RefreshToken
from fastapi_app.models.role_model import Role

# ============================================================================
# DATA SOURCE MODELS
# ============================================================================
from fastapi_app.models.data_source_model import DataSource, DataSourceType, DataSourceProvider
from fastapi_app.models.connection_history_model import ConnectionHistory
from fastapi_app.models.sync_log_model import SyncLog
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.validation_error_model import ValidationError

# ============================================================================
# RAW DATA MODELS
# ============================================================================
from fastapi_app.models.raw_data_model import (
    RawSales,
    RawInventory,
    RawSupplier,
    RawProducts
)

# ============================================================================
# SYNC & UPLOAD JOB MODELS
# ============================================================================
from fastapi_app.models.sync_job_model import (
    SyncJob,
    SyncJobStatus,
    SyncJobStep,
    SyncJobStepDetail
)
from fastapi_app.models.upload_job_model import (
    UploadJob,
    UploadJobStatus,
    UploadJobStep,
    UploadJobStepDetail
)

# ============================================================================
# PROCESSING JOB MODELS
# ============================================================================
from fastapi_app.models.processing_job_model import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobStep,
    ProcessingJobStepDetail,
    ProcessingJobLog,
    ProcessingOutlierResult,
    ProcessingGeneratedFeature
)

# ============================================================================
# FORECAST MODELS
# ============================================================================
from fastapi_app.models.forecast_job_model import (
    ForecastJob,
    ForecastJobStatus,
    ForecastJobStep,
    ForecastJobStepDetail,
    ForecastResult
)
from fastapi_app.models.forecast_metric_history_model import ForecastMetricHistory
from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.models.training_job_model import TrainingJob, TrainingHistory, TrainingJobStepDetail
from fastapi_app.models.training_configuration_model import TrainingConfiguration

# ============================================================================
# RECOMMENDATION MODELS
# ============================================================================
from fastapi_app.models.recommendation_result_model import (
    RecommendationResult,
    RecommendationResultStatus,
    RecommendationResultPriority,
    RecommendationResultType,
    RecommendationResultCategory
)
from fastapi_app.models.recommendation_history_model import RecommendationHistory

# ============================================================================
# NOTIFICATION MODELS
# ============================================================================
from fastapi_app.models.notification_model import (
    Notification,
    NotificationStatus,
    NotificationPriority,
    NotificationType
)

# ============================================================================
# INVENTORY MODELS - UPDATED (Includes SafetyStockCalculation)
# ============================================================================
from fastapi_app.models.inventory_model import (
    InventorySKU,
    WarehouseInventory,
    SafetyStockCalculation,  # ✅ Added back
    ReorderPoint,
    InventoryTransfer,
    ExcessStock,
    SlowMovingInventory,
    InventoryHistory,
    InventoryMovement,
    InventoryAlert,
)

# ============================================================================
# SCHEDULER MODELS
# ============================================================================
from fastapi_app.models.scheduler_history_model import SchedulerHistory

# ============================================================================
# SCENARIO MODELS
# ============================================================================
from fastapi_app.models.scenario_model import (
    Scenario,
    ScenarioStatus,
    ScenarioRun,
    ScenarioResult,
    ScenarioComparison
)

# ============================================================================
# REPORT MODELS
# ============================================================================
from fastapi_app.models.report_model import Report


__all__ = [
    # Alert
    'Alert',
    
    # Auth
    'User',
    'AuthAuditLog',
    'OtpRecord',
    'Permission',
    'RefreshToken',
    'Role',
    
    # Data Sources
    'DataSource',
    'DataSourceType',
    'DataSourceProvider',
    'ConnectionHistory',
    'SyncLog',
    'Upload',
    'ValidationError',
    
    # Raw Data
    'RawSales',
    'RawInventory',
    'RawSupplier',
    'RawProducts',
    
    # Sync & Upload Jobs
    'SyncJob',
    'SyncJobStatus',
    'SyncJobStep',
    'SyncJobStepDetail',
    'UploadJob',
    'UploadJobStatus',
    'UploadJobStep',
    'UploadJobStepDetail',
    
    # Processing Jobs
    'ProcessingJob',
    'ProcessingJobStatus',
    'ProcessingJobStep',
    'ProcessingJobStepDetail',
    'ProcessingJobLog',
    'ProcessingOutlierResult',
    'ProcessingGeneratedFeature',
    
    # Forecast
    'ForecastJob',
    'ForecastJobStatus',
    'ForecastJobStep',
    'ForecastJobStepDetail',
    'ForecastResult',
    'ForecastMetricHistory',
    'ModelRegistry',
    'TrainingJob',
    'TrainingHistory',
    'TrainingJobStepDetail',
    'TrainingConfiguration',
    
    # Recommendation
    'RecommendationResult',
    'RecommendationResultStatus',
    'RecommendationResultPriority',
    'RecommendationResultType',
    'RecommendationResultCategory',
    'RecommendationHistory',
    
    # Notifications
    'Notification',
    'NotificationStatus',
    'NotificationPriority',
    'NotificationType',
    
    # Inventory - UPDATED 
    'InventorySKU',
    'WarehouseInventory',
    'SafetyStockCalculation',  
    'ReorderPoint',
    'InventoryTransfer',
    'ExcessStock',
    'SlowMovingInventory',
    'InventoryHistory',
    'InventoryMovement',
    'InventoryAlert',
    
    # Scheduler
    'SchedulerHistory',
    
    # Scenario
    'Scenario',
    'ScenarioStatus',
    'ScenarioRun',
    'ScenarioResult',
    'ScenarioComparison',
    
    # Report
    'Report',
]