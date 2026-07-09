import time
import logging
from pathlib import Path
from datetime import datetime

from fastapi_app.db.session import SessionLocal
from fastapi_app.models.training_job_model import TrainingJob
from fastapi_app.models.model_registry_model import ModelRegistry
from fastapi_app.services.forecast.forecast_service import (
    prepare_series,
)
from fastapi_app.ai import arima, xgboost_model, lstm, prophet as prophet_ai
from fastapi_app.core.config import MODELS_DIR
import joblib
import torch

LOG = logging.getLogger("training_worker")
LOG.setLevel(logging.INFO)


def _save_xgb_model(model, path: str):
    joblib.dump(model, path)


def _save_lstm_model(model, path: str):
    # Save state dict for lightweight persistence
    torch.save(model.state_dict(), path)


def _save_prophet_model(model, path: str):
    joblib.dump(model, path)


def process_job(job_row: TrainingJob):
    db = SessionLocal()
    try:
        # mark in progress
        job_row.status = "in_progress"
        job_row.updated_at = datetime.utcnow()
        db.commit()

        csv_path = job_row.csv_path
        # get series
        try:
            series = prepare_series(csv_path)
        except FileNotFoundError:
            series = None

        metrics = {}
        model_path = None

        if job_row.model_type == "arima":
            fitted = arima.train_arima(series.tolist() if series is not None else [])
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            model_path = str(Path(MODELS_DIR) / f"arima_{ts}.pkl")
            arima.save_model(fitted, model_path)
            metrics = {"aic": float(getattr(fitted, "aic", 0))}

        elif job_row.model_type == "xgboost":
            model = xgboost_model.train_xgboost(series.tolist(), n_lags=7)
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            model_path = str(Path(MODELS_DIR) / f"xgboost_{ts}.joblib")
            _save_xgb_model(model, model_path)
            eval_metrics = xgboost_model.evaluate_xgboost(model, series.tolist(), n_lags=7)
            metrics = {k: eval_metrics[k] for k in ("mse", "rmse", "mae") if k in eval_metrics}

        elif job_row.model_type == "lstm":
            model = lstm.train_lstm(series.tolist(), n_lags=7, epochs=5)
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            model_path = str(Path(MODELS_DIR) / f"lstm_{ts}.pt")
            _save_lstm_model(model, model_path)
            eval_metrics = lstm.evaluate_lstm(model, series.tolist(), n_lags=7)
            metrics = {k: eval_metrics[k] for k in ("mse", "rmse", "mae") if k in eval_metrics}

        elif job_row.model_type == "prophet":
            try:
                model, train_df, test_df = prophet_ai.train_prophet(series.tolist())
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
                model_path = str(Path(MODELS_DIR) / f"prophet_{ts}.joblib")
                _save_prophet_model(model, model_path)
                eval_metrics = prophet_ai.evaluate_prophet(model, test_df)
                metrics = {k: eval_metrics[k] for k in ("mse", "rmse", "mae") if k in eval_metrics}
            except Exception:
                metrics = {}

        # Register model in DB if saved
        if model_path:
            reg = ModelRegistry(name=f"auto_{job_row.model_type}", model_type=job_row.model_type, version="v1", path=model_path, meta_info={})
            db.add(reg)
            db.commit()

        # Mark job completed
        job_row.status = "completed"
        job_row.metrics = metrics
        job_row.completed_at = datetime.utcnow()
        job_row.updated_at = datetime.utcnow()
        db.commit()

    except Exception:
        LOG.exception("Failed processing training job %s", job_row.job_id)
        job_row.status = "failed"
        job_row.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def run_worker(poll_seconds: int = 5):
    LOG.info("Starting training worker (poll %ss)", poll_seconds)
    while True:
        db = SessionLocal()
        try:
            job = db.query(TrainingJob).filter(TrainingJob.status == "queued").order_by(TrainingJob.created_at).first()
            if job:
                LOG.info("Processing job %s type=%s", job.job_id, job.model_type)
                process_job(job)
        except Exception:
            LOG.exception("Worker loop error")
        finally:
            db.close()

        time.sleep(poll_seconds)


def start_training_worker_thread(poll_seconds: int = 5):
    import threading

    t = threading.Thread(target=run_worker, args=(poll_seconds,), daemon=True)
    t.start()
    LOG.info("Training worker thread started")
