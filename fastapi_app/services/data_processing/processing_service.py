from typing import List, Dict


def start_processing() -> dict:
    return {"status": "started", "message": "Processing pipeline started"}


def stop_processing() -> dict:
    return {"status": "stopped", "message": "Processing pipeline stopped"}


def get_processing_pipeline() -> dict:
    return {
        "pipeline": [
            {"step": 1, "name": "load"},
            {"step": 2, "name": "clean"},
            {"step": 3, "name": "feature_engineer"},
        ]
    }


def get_outliers() -> List[dict]:
    return [
        {"column": "Demand", "outliers": 5},
    ]


def get_features() -> List[dict]:
    return [
        {"feature": "rolling_mean", "description": "7-day rolling average"},
    ]


def get_processing_logs() -> List[dict]:
    return [
        {"timestamp": "2026-06-16T00:00:00Z", "message": "Processing completed"},
    ]
