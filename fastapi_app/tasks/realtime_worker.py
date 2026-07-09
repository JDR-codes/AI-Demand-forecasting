import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi_app.db.session import SessionLocal
from fastapi_app.services.forecast.forecast_service import auto_forecast_report
from fastapi_app.services.forecast.forecast_db_service import ForecastGenerationService
from fastapi_app.schemas.forecast_schema import ForecastCreate

LOG = logging.getLogger("realtime_worker")
LOG.setLevel(logging.INFO)


class RealtimeCSVWatcher:
    """Simple folder watcher that polls `media/uploads/csv` for new CSV files
    and runs the forecasting pipeline when new files appear. Results are
    persisted to the `forecasts` table via `ForecastGenerationService`.
    """

    def __init__(self, watch_dir: str | Path, poll_seconds: int = 5):
        self.watch_dir = Path(watch_dir)
        self.poll_seconds = poll_seconds
        self.state_file = Path("model_artifacts/processed_files.json")
        os.makedirs(self.state_file.parent, exist_ok=True)
        self._load_state()

    def _load_state(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.processed = set(json.load(f))
            except Exception:
                self.processed = set()
        else:
            self.processed = set()

    def _save_state(self) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(list(self.processed), f)

    def _is_csv(self, path: Path) -> bool:
        return path.suffix.lower() in {".csv"}

    def process_file(self, file_path: Path, forecast_steps: int = 7) -> None:
        LOG.info("Processing new file: %s", file_path)
        try:
            report = auto_forecast_report(path=str(file_path), forecast_steps=forecast_steps)

            # report can include per-model entries or a single model field
            models_to_persist: Dict[str, Any] = {}
            for m in ("arima", "xgboost", "lstm", "prophet"):
                if m in report:
                    models_to_persist[m] = report[m]

            # Fall back: if report contains a single `model` key
            if not models_to_persist and "model" in report:
                models_to_persist[report.get("requested_model", "auto")] = report["model"]

            sku = file_path.stem

            db = SessionLocal()
            try:
                for model_name, model_report in models_to_persist.items():
                    # Extract a sensible numeric prediction from the model report
                    predicted = 0.0
                    try:
                        if isinstance(model_report, dict) and "forecast" in model_report:
                            f = model_report["forecast"]
                        elif isinstance(model_report, dict) and "future_predictions" in model_report:
                            f = model_report["future_predictions"]
                        else:
                            f = model_report

                        # f may be list-like; pick first element
                        if hasattr(f, "__len__") and len(f) > 0:
                            predicted = float(f[0])
                        else:
                            predicted = float(f)
                    except Exception:
                        predicted = 0.0

                    forecast_data = ForecastCreate(
                        model_id=None,
                        sku=sku,
                        region="default",
                        warehouse="default",
                        horizon=forecast_steps,
                        predicted_demand=predicted,
                        confidence_score=0.8,
                        model_used=model_name,
                    )

                    try:
                        ForecastGenerationService.generate_forecast(db, forecast_data)
                    except Exception:
                        LOG.exception("Failed to persist forecast for %s", model_name)

                db.commit()
            finally:
                db.close()

            # mark processed
            self.processed.add(str(file_path.resolve()))
            self._save_state()

        except Exception:
            LOG.exception("Failed processing file: %s", file_path)

    def run(self, forecast_steps: int = 7) -> None:
        LOG.info("Starting RealtimeCSVWatcher on %s", self.watch_dir)
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                for p in sorted(self.watch_dir.iterdir()):
                    if not p.is_file() or not self._is_csv(p):
                        continue
                    resolved = str(p.resolve())
                    if resolved in self.processed:
                        continue
                    # attempt to process
                    self.process_file(p, forecast_steps=forecast_steps)
            except Exception:
                LOG.exception("Error during watch loop")

            time.sleep(self.poll_seconds)


def start_realtime_watcher_in_thread(watch_dir: str | Path = "fastapi_app/media/uploads/csv", poll_seconds: int = 5, forecast_steps: int = 7):
    import threading

    watcher = RealtimeCSVWatcher(watch_dir=watch_dir, poll_seconds=poll_seconds)
    t = threading.Thread(target=watcher.run, args=(forecast_steps,), daemon=True)
    t.start()
    LOG.info("Realtime watcher thread started")
