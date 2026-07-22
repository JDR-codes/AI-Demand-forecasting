# main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# ROUTER IMPORTS
# ============================================================================

from fastapi_app.routes.auth_router import api_router
from fastapi_app.routes.roles import router as roles_router
from fastapi_app.routes.data_sources import router as data_sources_router
from fastapi_app.routes.uploads import router as uploads_router
from fastapi_app.routes.validation import router as validation_router
from fastapi_app.routes.validation_dashboard import router as validation_dashboard_router
from fastapi_app.routes.processing import router as processing_router
from fastapi_app.routes.processing_details import router as processing_details_router
from fastapi_app.routes.processing_history import router as processing_history_router
from fastapi_app.routes.processing_statistics import router as processing_statistics_router
from fastapi_app.routes.data_processing import router as data_processing_router
from fastapi_app.routes.notifications import router as notifications_router
from fastapi_app.routes.scheduler import router as scheduler_router
from fastapi_app.routes.websocket import router as websocket_router
from fastapi_app.routes.dashboard import router as dashboard_router

# Forecast routes
from fastapi_app.routes.forecast_jobs import router as forecast_jobs_router
from fastapi_app.routes.training_jobs import router as training_jobs_router
from fastapi_app.routes.model_registry import router as models_router
from fastapi_app.routes.forecast_engine import router as forecast_engine_router

# ✅ Recommendation routes
from fastapi_app.routes.recommendation import router as recommendation_router

# Inventory & Other
from fastapi_app.routes.inventory import router as inventory_router
from fastapi_app.routes.scenarios import router as scenarios_router
from fastapi_app.routes.alerts_module13 import router as alerts_module13_router
from fastapi_app.routes.reports_module14 import router as reports_router
from fastapi_app.routes.mock_router import router as mock_router

from fastapi_app.db.session import init_db
from fastapi_app.services.scheduler.scheduler_service import scheduler


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting application...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
    
    # Start scheduler
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        scheduler.stop()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {str(e)}")


# ============================================================================
# CREATE APP
# ============================================================================

app = FastAPI(
    title='Demand Forecasting Backend',
    description='Enterprise Demand Forecasting Platform',
    version='2.0.0',
    lifespan=lifespan
)

# ============================================================================
# STATIC FILES
# ============================================================================

MEDIA_ROOT = Path("fastapi_app/media")
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

app.mount(
    "/media",
    StaticFiles(directory=MEDIA_ROOT),
    name="media"
)

# ============================================================================
# ROUTER REGISTRATION
# ============================================================================

# Auth & Users
app.include_router(api_router)                       # /api/auth
app.include_router(roles_router)                     # /api/roles

# Data Sources & Uploads
app.include_router(data_sources_router)              # /api/data-sources
app.include_router(uploads_router)                   # /api/uploads
app.include_router(validation_router)                # /api/validation
app.include_router(validation_dashboard_router)      # /api/validation/dashboard

# Data Processing Pipeline
app.include_router(data_processing_router)           # /api/data-processing
app.include_router(processing_router)                # /api/processing
app.include_router(processing_details_router)        # /api/processing/details
app.include_router(processing_history_router)        # /api/processing/history
app.include_router(processing_statistics_router)     # /api/processing/statistics

# Notifications
app.include_router(notifications_router)             # /api/notifications

# Scheduler
app.include_router(scheduler_router)                 # /api/scheduler

# WebSocket
app.include_router(websocket_router)                 # /ws

# Forecast Module
app.include_router(forecast_jobs_router)             # /api/forecast/jobs
app.include_router(training_jobs_router)             # /api/training
app.include_router(models_router)                    # /api/forecast/models
app.include_router(forecast_engine_router)           # /api/forecast

# ✅ Recommendation Module - NEW
app.include_router(recommendation_router)            # /api/recommendations

# Inventory & Scenarios
app.include_router(inventory_router)                 # /api/inventory
app.include_router(scenarios_router)                 # /api/scenarios

# Alerts & Reports
app.include_router(alerts_module13_router)           # /api/alerts
app.include_router(reports_router)                   # /api/reports

# Dashboard & Mock
app.include_router(dashboard_router)                 # /api/dashboard
app.include_router(mock_router)                      # /api/mock

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Demand Forecasting Backend",
        "version": "2.0.0"
    }


@app.get("/")
async def root():
    return {
        "message": "Demand Forecasting Backend API",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }