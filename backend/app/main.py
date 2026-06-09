from fastapi import FastAPI
from app.api.version1.router import api_router

app = FastAPI(title='Demand Forecasting Backend')
app.include_router(api_router)
