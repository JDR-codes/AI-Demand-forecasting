# main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Capture warnings in logging system for cleaner output formatting
logging.captureWarnings(True)

# ============================================================================
# ROUTER IMPORTS
# ============================================================================

# Auth & Users
from fastapi_app.routes.auth_router import router as auth_router
from fastapi_app.routes.users import router as users_router

# Audit Logs
from fastapi_app.routes.audit_logs import router as audit_log_router

# Data Sources, Uploads & Scheduler
from fastapi_app.routes.data_sources import router as data_sources_router
from fastapi_app.routes.scheduler import router as scheduler_router
from fastapi_app.routes.uploads import router as uploads_router
from fastapi_app.routes.validation import router as validation_router

# Data Processing Pipeline
from fastapi_app.routes.processing import router as processing_router
from fastapi_app.routes.processing_details import router as processing_details_router

# Notifications
from fastapi_app.routes.notifications import router as notifications_router

# WebSocket
from fastapi_app.routes.websocket import router as websocket_router




# Forecast Module
from fastapi_app.routes.forecast_jobs import router as forecast_jobs_router
from fastapi_app.routes.training_jobs import router as training_jobs_router
from fastapi_app.routes.model_registry import router as models_router
from fastapi_app.routes.forecast_engine import router as forecast_engine_router

# Recommendations
from fastapi_app.routes.recommendation import router as recommendation_router

# Scenarios
from fastapi_app.routes.scenarios import router as scenarios_router

# Inventory
from fastapi_app.routes.inventory import router as inventory_router

# Alerts & Reports
from fastapi_app.routes.alerts_router import router as alerts_router
from fastapi_app.routes.reports_router import router as reports_router

# Dashboard & Mock
from fastapi_app.routes.dashboard import router as dashboard_router
from fastapi_app.routes.mock_router import router as mock_router

# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

import asyncio
from fastapi_app.db.session import init_db
from fastapi_app.services.scheduler.scheduler_service import scheduler
from fastapi_app.services.websocket.websocket_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting application...")
    manager.set_loop(asyncio.get_running_loop())

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")

    # Start scheduler - this will automatically restore schedules from DB
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
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
app.include_router(auth_router)                       # /api/auth
app.include_router(users_router)                      # /api/users

# Audit Logs
app.include_router(audit_log_router)                 # /api/audit-logs

# Dashboard
app.include_router(dashboard_router)                 # /api/dashboard

# Data Sources, Uploads & Scheduler
app.include_router(data_sources_router)              # /api/data-sources
app.include_router(scheduler_router)                 # /api/scheduler
app.include_router(uploads_router)                   # /api/uploads
app.include_router(validation_router)                # /api/validation




# Data Processing Pipeline
app.include_router(processing_router)                # /api/processing
app.include_router(processing_details_router)        # /api/processing/details



# Forecast Module
app.include_router(training_jobs_router)             # /api/training
app.include_router(forecast_engine_router)           # /api/forecast
app.include_router(models_router)                    # /api/forecast/models
app.include_router(forecast_jobs_router)             # /api/forecast/jobs

# Recommendations
app.include_router(recommendation_router)            # /api/recommendations

# Scenarios
app.include_router(scenarios_router)                 # /api/scenarios

# Inventory
app.include_router(inventory_router)                 # /api/inventory

# Alerts & Reports
app.include_router(alerts_router)                    # /api/alerts
app.include_router(reports_router)                   # /api/reports

# Notifications
app.include_router(notifications_router)             # /api/notifications

# WebSocket
app.include_router(websocket_router)                 # /ws

# Mock APIs (Development only)
app.include_router(mock_router)                      # /mock

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