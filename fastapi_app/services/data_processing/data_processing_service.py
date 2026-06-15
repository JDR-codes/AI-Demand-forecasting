import pandas as pd
from typing import Iterable, List
import os
import numpy as np


def series_from_list(values: Iterable[float]) -> pd.Series:
    return pd.Series(list(values))


def simple_resample(series: pd.Series, rule: str = "D") -> pd.Series:
    # Assumes index is datetime-like; if not, return original
    try:
        s = series.copy()
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.date_range(start="2020-01-01", periods=len(s), freq=rule)
        return s.resample(rule).mean()
    except Exception:
        return series


def normalize(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / (series.std() + 1e-9)


def load_csv(path: str, date_col: str | None = None, parse_dates: bool = True) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if parse_dates and date_col:
        return pd.read_csv(path, parse_dates=[date_col])
    return pd.read_csv(path)


def select_value_column(df: pd.DataFrame, value_col: str | None = None) -> pd.Series:
    if value_col and value_col in df.columns:
        return df[value_col]
    # prefer numeric columns
    numeric_cols = df.select_dtypes(include=[float, int]).columns.tolist()
    if numeric_cols:
        return df[numeric_cols[0]]
    # fallback to first column
    return df.iloc[:, 0]


def handle_missing(series: pd.Series, method: str = "interpolate") -> pd.Series:
    if method == "drop":
        return series.dropna()
    if method == "ffill":
        return series.fillna(method="ffill")
    # default interpolate
    try:
        return series.interpolate().fillna(method="bfill").fillna(method="ffill")
    except Exception:
        return series.fillna(series.mean())


def remove_outliers(series: pd.Series, z_thresh: float = 3.0) -> pd.Series:
    arr = series.to_numpy(dtype=float)
    mean = np.nanmean(arr)
    std = np.nanstd(arr)
    if std == 0 or np.isnan(std):
        return series
    zscores = np.abs((arr - mean) / std)
    return series.where(zscores <= z_thresh)
