#fastapi_app/routes/data_processing.py
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Tuple, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.core.config import DEFAULT_DATASET_PATH, DATA_DIR
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.services.forecast.forecast_service import train_and_register
from fastapi_app.services.data_processing.feature_engineering_service import (
    detect_outliers_advanced,
    generate_features_advanced
)
import pandas as pd
import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST MODELS
# ============================================================================

class ProcessRequest(BaseModel):
    series: list[float]
    resample_rule: str = "D"
    normalize: bool = False


class CSVProcessRequest(BaseModel):
    path: str | None = None
    date_column: str | None = None
    value_column: str | None = None
    parse_dates: bool = True
    missing_method: str = "interpolate"
    remove_outliers: bool = True
    z_thresh: float = 3.0
    resample_rule: str = "D"
    normalize: bool = False
    train: bool = False
    model_name: str | None = None
    order: Tuple[int, int, int] = (1, 1, 1)


class OutlierRequest(BaseModel):
    series: list[float]
    method: str = "zscore"
    threshold: float = 3.0


class FeatureRequest(BaseModel):
    series: list[float]
    lags: List[int] = Field(default_factory=lambda: [7, 14, 30])
    rolling_windows: List[int] = Field(default_factory=lambda: [7, 14, 30])
    include_cyclical: bool = True
    include_binary: bool = True


class AggregationRequest(BaseModel):
    series: list[float]
    group_by: str = "day"


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/api/data-processing",
    tags=["Data Processing"]
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/series")
def process_series(
    req: ProcessRequest,
    current_user: User = Depends(get_current_user)
):
    if not req.series:
        raise HTTPException(status_code=400, detail="empty series")
    
    s = pd.Series(req.series)
    
    try:
        s.index = pd.date_range(start="2020-01-01", periods=len(s), freq=req.resample_rule)
        s = s.resample(req.resample_rule).mean()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Resampling failed: {str(e)}")
    
    if req.normalize:
        s = (s - s.mean()) / (s.std() + 1e-9)
    
    return {"processed": [float(x) for x in s.tolist() if not pd.isna(x)]}


@router.post("/from-csv")
def process_from_csv(
    req: CSVProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    csv_path = req.path if req.path else DEFAULT_DATASET_PATH
    
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"File not found: {csv_path}")

    # Inspect CSV headers to find actual case-sensitive column name for date_column
    actual_date_col = None
    try:
        header_df = pd.read_csv(csv_path, nrows=0)
        col_map = {c.lower(): c for c in header_df.columns}
        if req.date_column:
            actual_date_col = col_map.get(req.date_column.lower())
    except Exception:
        pass

    try:
        if req.parse_dates and actual_date_col:
            df = pd.read_csv(csv_path, parse_dates=[actual_date_col])
        else:
            df = pd.read_csv(csv_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {csv_path}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Handle date column index
    date_col_to_use = actual_date_col or req.date_column
    if date_col_to_use and date_col_to_use in df.columns:
        df[date_col_to_use] = pd.to_datetime(df[date_col_to_use], errors="coerce")
        df = df.set_index(date_col_to_use)
    else:
        for col in df.columns:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df = df.set_index(col)
                    break
                if df[col].astype(str).str.match(r"\d{4}-\d{2}-\d{2}").any():
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    df = df.set_index(col)
                    break
            except Exception:
                continue

    # Select value column - improved case-insensitive detection
    series = _select_value_column(df, req.value_column)

    # Handle missing values - modernized
    if req.missing_method == "drop":
        series = series.dropna()
    elif req.missing_method == "ffill":
        series = series.ffill()
    elif req.missing_method == "bfill":
        series = series.bfill()
    elif req.missing_method == "interpolate":
        series = series.interpolate().bfill().ffill()
    else:
        series = series.fillna(series.mean())

    # Remove outliers
    if req.remove_outliers:
        arr = series.to_numpy(dtype=float)
        mean = np.nanmean(arr)
        std = np.nanstd(arr)
        if std > 0 and not np.isnan(std):
            zscores = np.abs((arr - mean) / std)
            series = series.where(zscores <= req.z_thresh).dropna()

    # Resample
    if req.resample_rule:
        try:
            if not isinstance(series.index, pd.DatetimeIndex):
                series.index = pd.date_range(start="2020-01-01", periods=len(series), freq=req.resample_rule)
            series = series.resample(req.resample_rule).mean()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Resampling failed: {str(e)}")

    # Normalize
    if req.normalize:
        series = (series - series.mean()) / (series.std() + 1e-9)

    # Save processed series
    os.makedirs(DATA_DIR, exist_ok=True)
    source_name = os.path.basename(csv_path)
    dest = os.path.join(DATA_DIR, f"processed_{source_name}")
    series.to_csv(dest, index=True, header=True)

    resp = {"processed_path": dest, "length": int(series.dropna().shape[0])}

    if req.train:
        model_path = train_and_register(
            series.dropna().tolist(),
            order=tuple(req.order),
            name=req.model_name
        )
        resp["model_path"] = model_path

    return resp


def _select_value_column(df: pd.DataFrame, value_col: str | None = None) -> pd.Series:
    """Improved value column detection with case-insensitivity."""
    if value_col:
        if value_col in df.columns:
            return df[value_col]
        for col in df.columns:
            if col.lower() == value_col.lower():
                return df[col]
    
    # Preferred column names (case-insensitive)
    preferred = ["demand", "sales", "quantity", "units", "units sold", "stock", "value", "amount", "price", "revenue"]
    for pref in preferred:
        for col in df.columns:
            if col.lower() == pref:
                return df[col]
    
    # Fallback to numeric columns
    numeric_cols = df.select_dtypes(include=[np.number, float, int]).columns.tolist()
    if numeric_cols:
        return df[numeric_cols[0]]
    
    # Final fallback to first column
    return df.iloc[:, 0]


@router.post("/detect-outliers")
def detect_outliers(
    req: OutlierRequest,
    current_user: User = Depends(get_current_user)
):
    """Advanced outlier detection with multiple methods."""
    if not req.series:
        raise HTTPException(status_code=400, detail="empty series")
    
    result = detect_outliers_advanced(req.series, req.method, req.threshold)
    return result


@router.post("/generate-features")
def generate_features(
    req: FeatureRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate time series features matching Figma design."""
    if not req.series:
        raise HTTPException(status_code=400, detail="empty series")
    
    result = generate_features_advanced(
        req.series,
        req.lags,
        req.rolling_windows,
        req.include_cyclical,
        req.include_binary
    )
    return result


@router.post("/aggregate")
def aggregate_data(
    req: AggregationRequest,
    current_user: User = Depends(get_current_user)
):
    """Aggregate time series data by time period."""
    if not req.series:
        raise HTTPException(status_code=400, detail="empty series")
    
    s = pd.Series(req.series)
    s.index = pd.date_range(start='2024-01-01', periods=len(s), freq='D')
    
    rule_map = {
        "day": "D",
        "week": "W",
        "month": "M",
        "quarter": "Q"
    }
    rule = rule_map.get(req.group_by, "D")
    
    aggregated = s.resample(rule).sum()
    
    return {
        "original_length": len(s),
        "aggregated_length": len(aggregated),
        "group_by": req.group_by,
        "aggregated": [float(x) for x in aggregated.tolist() if not pd.isna(x)],
        "indices": [str(idx) for idx in aggregated.index.tolist()[:100]]
    }