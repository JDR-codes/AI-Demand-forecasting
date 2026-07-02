from fastapi import FastAPI
from fastapi_app.routes.auth_router import api_router
from fastapi_app.routes.roles import router as roles_router
from fastapi_app.routes.data_integration import router as data_integration_router
from fastapi_app.routes.data_processing import router as data_processing_router
from fastapi_app.routes.forecast import router as forecast_router
from fastapi_app.routes.recommendation import router as recommendation_router
from fastapi_app.routes.data_sources import router as data_sources_router
from fastapi_app.routes.uploads import router as uploads_router
from fastapi_app.routes.validation import router as validation_router
from fastapi_app.routes.processing import router as processing_router
from fastapi_app.routes.forecast_engine import router as forecast_engine_router
from fastapi_app.routes.forecast_module9 import router as forecast_module9_router
from fastapi_app.routes.recommendation_module10 import router as recommendation_module10_router
from fastapi_app.routes.inventory import router as inventory_router
from fastapi_app.routes.scenarios import router as scenarios_router
from fastapi_app.routes.alerts_module13 import router as alerts_module13_router
from fastapi_app.routes.reports_module14 import router as reports_router
from fastapi_app.routes.dashboard import router as dashboard_router
from fastapi_app.db.session import init_db
# Import models so they are registered with SQLAlchemy before init_db()
from fastapi_app.models.auth_model import User  # noqa: F401
from fastapi_app.models.data_source_model import DataSource  # noqa: F401
from fastapi_app.models.upload_model import Upload  # noqa: F401
from fastapi_app.models.validation_error_model import ValidationError  # noqa: F401
from fastapi_app.models.forecast_model import Forecast  # noqa: F401
from fastapi_app.models.recommendation_model import Recommendation  # noqa: F401
from fastapi_app.models.inventory_model import InventorySKU, WarehouseInventory, SafetyStockCalculation, ReorderPoint, InventoryTransfer, ExcessStock  # noqa: F401
from fastapi_app.models.scenario_model import Scenario  # noqa: F401

from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title='Demand Forecasting Backend')

MEDIA_ROOT = Path("fastapi_app/media")
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

app.mount(
    "/media",
    StaticFiles(directory=MEDIA_ROOT),
    name="media"
)

# Initialize database on startup
init_db()

app.include_router(api_router)
app.include_router(roles_router)
app.include_router(data_sources_router)
app.include_router(uploads_router)
app.include_router(validation_router)
app.include_router(processing_router)
app.include_router(forecast_engine_router)
app.include_router(forecast_module9_router)
app.include_router(recommendation_module10_router)
app.include_router(inventory_router)
app.include_router(scenarios_router)
app.include_router(alerts_module13_router)
app.include_router(reports_router)
app.include_router(dashboard_router)

# app.include_router(data_integration_router)
# app.include_router(data_processing_router)
# app.include_router(forecast_router)
# app.include_router(recommendation_router)
