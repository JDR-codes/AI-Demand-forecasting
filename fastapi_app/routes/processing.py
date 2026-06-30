from fastapi import APIRouter, Depends
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.models.auth_model import User
from fastapi_app.services.data_processing.processing_service import (
    start_processing,
    stop_processing,
    get_processing_pipeline,
    get_outliers,
    get_features,
    get_processing_logs,
)

router = APIRouter(prefix="/api/processing", tags=["Processing"])


@router.post("/start")
def start_processing_endpoint(current_user: User = Depends(get_current_user)):
    return start_processing()


@router.post("/stop")
def stop_processing_endpoint(current_user: User = Depends(get_current_user)):
    return stop_processing()


@router.get("/pipeline")
def pipeline_endpoint(current_user: User = Depends(get_current_user)):
    return get_processing_pipeline()


@router.get("/outliers")
def outliers_endpoint(current_user: User = Depends(get_current_user)):
    return get_outliers()


@router.get("/features")
def features_endpoint(current_user: User = Depends(get_current_user)):
    return get_features()


@router.get("/logs")
def logs_endpoint(current_user: User = Depends(get_current_user)):
    return get_processing_logs()
