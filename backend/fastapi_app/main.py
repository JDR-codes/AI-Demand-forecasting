from fastapi import FastAPI
from fastapi_app.api.version1.routes.auth_router import api_router
from fastapi_app.db.session import init_db
# Import models so they are registered with SQLAlchemy before init_db()
from fastapi_app.models.auth_model import User  # noqa: F401

app = FastAPI(title='Demand Forecasting Backend')

# Initialize database on startup
init_db()

app.include_router(api_router)
