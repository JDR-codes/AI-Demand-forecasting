from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi_app.services.data_processing.data_processing_service import (
    series_from_list,
    simple_resample,
    normalize,
    load_csv,
    select_value_column,
    handle_missing,
    remove_outliers,
)
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.core.config import DEFAULT_DATASET_PATH, DATA_DIR
from fastapi_app.models.auth_model import User
from fastapi_app.services.forecast.forecast_service import train_and_register
import pandas as pd
import os
from typing import Tuple


class ProcessRequest(BaseModel):
    series: list[float]
    resample_rule: str = "D"
    normalize: bool = False


class CSVProcessRequest(BaseModel):
    path: str | None = None
    date_column: str | None = None
    value_column: str | None = None
    parse_dates: bool = True
    missing_method: str = "interpolate"  # options: interpolate, drop, ffill
    remove_outliers: bool = True
    z_thresh: float = 3.0
    resample_rule: str = "D"
    normalize: bool = False
    train: bool = False
    model_name: str | None = None
    order: Tuple[int, int, int] = (1, 1, 1)


router = APIRouter(prefix="/api/data_process")


@router.post("/series")
def process_series(req: ProcessRequest, current_user: User = Depends(get_current_user)):
    if not req.series:
        raise HTTPException(status_code=400, detail="empty series")
    s = series_from_list(req.series)
    s = simple_resample(s, rule=req.resample_rule)
    if req.normalize:
        s = normalize(s)
    # Return numeric list
    return {"processed": [float(x) for x in s.tolist()]}


@router.post("/from-csv")
def process_from_csv(req: CSVProcessRequest, current_user: User = Depends(get_current_user)):
    # Determine CSV path automatically if not provided
    csv_path = req.path if req.path else DEFAULT_DATASET_PATH

    # Load CSV
    try:
        df = load_csv(csv_path, date_col=req.date_column, parse_dates=req.parse_dates)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Ensure date index if possible
    if req.date_column and req.date_column in df.columns:
        df[req.date_column] = pd.to_datetime(df[req.date_column], errors="coerce")
        df = df.set_index(req.date_column)
    else:
        # try to infer a datetime column
        for col in df.columns:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df = df.set_index(col)
                    break
                # quick string-detect
                if df[col].astype(str).str.match(r"\d{4}-\d{2}-\d{2}").any():
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    df = df.set_index(col)
                    break
            except Exception:
                continue

    # Select value column
    series = select_value_column(df, req.value_column)

    # Handle missing values
    series = handle_missing(series, method=req.missing_method)

    # Remove outliers
    if req.remove_outliers:
        series = remove_outliers(series, z_thresh=req.z_thresh).dropna()

    # Resample
    if req.resample_rule:
        series = simple_resample(series, rule=req.resample_rule)

    # Normalize
    if req.normalize:
        series = normalize(series)

    # Save processed series
    os.makedirs(DATA_DIR, exist_ok=True)
    source_name = os.path.basename(csv_path)
    dest = os.path.join(DATA_DIR, f"processed_{source_name}")
    # Save as CSV with index
    series.to_csv(dest, index=True, header=True)

    resp = {"processed_path": dest, "length": int(series.dropna().shape[0])}

    # Optionally train
    if req.train:
        model_path = train_and_register(series.dropna().tolist(), order=tuple(req.order), name=req.model_name)
        resp["model_path"] = model_path

    return resp
