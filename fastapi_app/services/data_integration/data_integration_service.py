import os
from typing import Optional


def save_uploaded_file(file_bytes: bytes, dest_path: str) -> str:
    """Save uploaded bytes to disk and return the path."""
    dirpath = os.path.dirname(dest_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return dest_path


def validate_csv_path(path: str) -> bool:
    return os.path.exists(path) and path.lower().endswith(".csv")
