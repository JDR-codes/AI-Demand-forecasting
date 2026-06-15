from fastapi import FastAPI
from fastapi_app.routes.auth_router import api_router
from fastapi_app.routes.data_integration import router as data_integration_router
from fastapi_app.routes.data_processing import router as data_processing_router
from fastapi_app.routes.forecast import router as forecast_router
from fastapi_app.routes.recommendation import router as recommendation_router
from fastapi_app.db.session import init_db
# Import models so they are registered with SQLAlchemy before init_db()
from fastapi_app.models.auth_model import User  # noqa: F401

app = FastAPI(title='Demand Forecasting Backend')

# Initialize database on startup
init_db()

app.include_router(api_router)
app.include_router(data_integration_router)
app.include_router(data_processing_router)
app.include_router(forecast_router)
app.include_router(recommendation_router)
