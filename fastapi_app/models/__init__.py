# fastapi_app/models/__init__.py
"""
Models package - import all models here for easy access.
All models are registered with Base.metadata when imported.
"""

from fastapi_app.models.alert_model import Alert
from fastapi_app.models.auth_model import User
from fastapi_app.models.data_source_model import DataSource
from fastapi_app.models.forecast_model import Forecast
from fastapi_app.models.inventory_model import (
    InventorySKU,
    WarehouseInventory,
    SafetyStockCalculation,
    ReorderPoint,
    InventoryTransfer,
    ExcessStock
)
from fastapi_app.models.otp_model import OtpRecord
from fastapi_app.models.permission_model import Permission
from fastapi_app.models.recommendation_model import Recommendation
from fastapi_app.models.report_model import Report
from fastapi_app.models.role_model import Role
from fastapi_app.models.scenario_model import Scenario
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.validation_error_model import ValidationError

# Export all models for easy import
__all__ = [
    'Alert',
    'User',
    'DataSource',
    'ExcessStock',
    'Forecast',
    'InventorySKU',
    'WarehouseInventory',
    'SafetyStockCalculation',
    'ReorderPoint',
    'InventoryTransfer',
    'OtpRecord',
    'Permission',
    'Recommendation',
    'Report',
    'Role',
    'Scenario',
    'Upload',
    'ValidationError',
]
