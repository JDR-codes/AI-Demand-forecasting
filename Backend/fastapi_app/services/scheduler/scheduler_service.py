# fastapi_app/services/scheduler/scheduler_service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Union
from zoneinfo import ZoneInfo
import asyncio

from requests import Session

from fastapi_app.db.session import SessionLocal
from fastapi_app.models.data_source_model import DataSource
from fastapi_app.models.sync_schedule_model import SyncSchedule

logger = logging.getLogger(__name__)

# Valid frequencies for validation
VALID_FREQUENCIES = ["manual", "hourly", "daily", "weekly", "monthly", "realtime"]

# Weekday mapping
WEEKDAY_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6
}

# Weekday abbreviations for cron
WEEKDAY_CRON = {
    "mon": "mon", "tue": "tue", "wed": "wed",
    "thu": "thu", "fri": "fri", "sat": "sat", "sun": "sun"
}


def parse_date(val: Union[str, date]) -> date:
    if isinstance(val, str):
        # Remove time or timezone info if present in string (e.g. 2026-08-04T09:00:00)
        val = val.split('T')[0]
        return date.fromisoformat(val)
    return val


def parse_time(val: Union[str, time]) -> time:
    if isinstance(val, str):
        # Strip timezone suffix (e.g. Z or +05:30)
        if 'Z' in val:
            val = val.replace('Z', '')
        if '+' in val:
            val = val.split('+')[0]
        if '.' in val:
            parts = val.split('.')
            time_part = parts[0]
            ms_part = parts[1][:6].ljust(6, '0') # Keep up to 6 digits for microseconds
            val = f"{time_part}.{ms_part}"
        return time.fromisoformat(val)
    return val


def parse_time_to_hour_minute(val: Union[str, time]) -> tuple[int, int]:
    if isinstance(val, time):
        return val.hour, val.minute
    if isinstance(val, str):
        # Strip timezone and fractional seconds
        val = val.replace('Z', '')
        if '+' in val:
            val = val.split('+')[0]
        if '.' in val:
            val = val.split('.')[0]
        parts = val.split(':')
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    raise ValueError(f"Unable to parse time: {val}")


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running_tasks = {}
        self._started = False

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                self.scheduler.start()
                self._started = True
                logger.info("Scheduler started")

                # Restore schedules from database
                self.restore_schedules()

            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self._started = False
            logger.info("Scheduler stopped")

    # ==========================================================================
    # RESTORE SCHEDULES
    # ==========================================================================

    def restore_schedules(self):
        """Restore all active schedules from database after restart."""
        db = SessionLocal()
        try:
            schedules = db.query(SyncSchedule).filter(
                SyncSchedule.is_active == True
            ).all()

            logger.info(f"Restoring {len(schedules)} active schedules")

            for schedule in schedules:
                try:
                    self.schedule_sync_from_db(db, schedule.id)
                except Exception as e:
                    logger.error(f"Failed to restore schedule {schedule.id}: {str(e)}")

            # Also restore legacy sync schedules
            self.schedule_all_syncs()

            # Restore retraining schedules
            self.schedule_all_trainings()

        except Exception as e:
            logger.error(f"Error restoring schedules: {str(e)}")
        finally:
            db.close()

    # ==========================================================================
    # SCHEDULE FROM DB
    # ==========================================================================

    def schedule_sync_from_db(self, db: Session, schedule_id: int) -> bool:
        """Schedule sync jobs from a SyncSchedule record."""
        schedule = db.query(SyncSchedule).filter(SyncSchedule.id == schedule_id).first()
        if not schedule:
            return False

        if not schedule.is_active:
            return False

        # Get data sources
        if schedule.scope == "all":
            sources = db.query(DataSource).filter(DataSource.is_enabled == True).all()
        else:
            if not schedule.data_source_ids:
                return False
            sources = db.query(DataSource).filter(
                DataSource.id.in_(schedule.data_source_ids),
                DataSource.is_enabled == True
            ).all()

        if not sources:
            logger.warning(f"No active sources found for schedule {schedule_id}")
            return False

        # Build jobs based on schedule type
        if schedule.schedule_type == "custom":
            jobs = self._build_custom_jobs(schedule)
        else:  # recurring
            jobs = self._build_recurring_jobs(schedule)

        if not jobs:
            return False

        # Add jobs to scheduler
        for datasource_id in [s.id for s in sources]:
            for job_info in jobs:
                job_id = f"schedule_{schedule_id}_{datasource_id}_{job_info.get('id', '')}"
                self.scheduler.add_job(
                    self._sync_job,
                    trigger=job_info["trigger"],
                    id=job_id,
                    args=[datasource_id],
                    replace_existing=True,
                    max_instances=1
                )
                self.running_tasks[job_id] = schedule_id
                logger.debug(f"Added job {job_id} for schedule {schedule_id}")

        return True

    def remove_schedule_jobs(self, schedule_id: int):
        """Remove all jobs associated with a schedule."""
        for job_id in list(self.running_tasks.keys()):
            if self.running_tasks[job_id] == schedule_id:
                self.scheduler.remove_job(job_id)
                del self.running_tasks[job_id]
                logger.debug(f"Removed job {job_id} for schedule {schedule_id}")

    # ==========================================================================
    # BUILD JOBS
    # ==========================================================================

    def _build_custom_jobs(self, schedule: SyncSchedule) -> List[Dict[str, Any]]:
        """Build DateTrigger jobs for custom schedule."""
        if not schedule.custom_runs:
            return []

        jobs = []
        tz = ZoneInfo(schedule.timezone)

        for i, run in enumerate(schedule.custom_runs):
            d = parse_date(run["date"])
            t = parse_time(run["time"])
            run_date = datetime.combine(d, t).replace(tzinfo=tz)

            jobs.append({
                "id": f"custom_{i}",
                "trigger": DateTrigger(run_date=run_date)
            })

        return jobs

    def _build_recurring_jobs(self, schedule: SyncSchedule) -> List[Dict[str, Any]]:
        """Build CronTrigger jobs for recurring schedule."""
        if schedule.frequency == "daily":
            return self._build_daily_jobs(schedule)
        elif schedule.frequency == "weekly":
            return self._build_weekly_jobs(schedule)
        elif schedule.frequency == "monthly":
            return self._build_monthly_jobs(schedule)
        else:
            return []

    def _build_daily_jobs(self, schedule: SyncSchedule) -> List[Dict[str, Any]]:
        """Build daily recurring jobs."""
        jobs = []
        tz = schedule.timezone

        if schedule.run_method == "fixed_time" and schedule.run_times:
            for i, run_time in enumerate(schedule.run_times):
                hour, minute = parse_time_to_hour_minute(run_time)

                # Apply date range if specified
                start_date = schedule.start_date
                end_date = schedule.end_date

                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=tz,
                    start_date=start_date,
                    end_date=end_date
                )
                jobs.append({
                    "id": f"daily_fixed_{i}",
                    "trigger": trigger
                })

        elif schedule.run_method == "interval":
            # Calculate times within window
            window_start = schedule.window_start_time
            window_end = schedule.window_end_time
            interval_minutes = self._get_interval_minutes(schedule)

            if not all([window_start, window_end, interval_minutes]):
                return jobs

            # Generate times within window
            current = datetime.combine(date.today(), window_start)
            end = datetime.combine(date.today(), window_end)

            while current <= end:
                jobs.append({
                    "id": f"daily_interval_{current.hour}_{current.minute}",
                    "trigger": CronTrigger(
                        hour=current.hour,
                        minute=current.minute,
                        timezone=tz,
                        start_date=schedule.start_date,
                        end_date=schedule.end_date
                    )
                })
                current += timedelta(minutes=interval_minutes)

        return jobs

    def _build_weekly_jobs(self, schedule: SyncSchedule) -> List[Dict[str, Any]]:
        """Build weekly recurring jobs."""
        jobs = []
        tz = schedule.timezone

        if not schedule.weekdays:
            return jobs

        # Convert weekdays to cron format
        weekdays_str = ",".join([WEEKDAY_CRON.get(d, d) for d in schedule.weekdays])

        if schedule.run_method == "fixed_time" and schedule.run_times:
            for i, run_time in enumerate(schedule.run_times):
                hour, minute = parse_time_to_hour_minute(run_time)

                trigger = CronTrigger(
                    day_of_week=weekdays_str,
                    hour=hour,
                    minute=minute,
                    timezone=tz,
                    start_date=schedule.start_date,
                    end_date=schedule.end_date
                )
                jobs.append({
                    "id": f"weekly_fixed_{i}",
                    "trigger": trigger
                })

        elif schedule.run_method == "interval":
            window_start = schedule.window_start_time
            window_end = schedule.window_end_time
            interval_minutes = self._get_interval_minutes(schedule)

            if not all([window_start, window_end, interval_minutes]):
                return jobs

            # Generate times within window
            current = datetime.combine(date.today(), window_start)
            end = datetime.combine(date.today(), window_end)

            while current <= end:
                trigger = CronTrigger(
                    day_of_week=weekdays_str,
                    hour=current.hour,
                    minute=current.minute,
                    timezone=tz,
                    start_date=schedule.start_date,
                    end_date=schedule.end_date
                )
                jobs.append({
                    "id": f"weekly_interval_{current.hour}_{current.minute}",
                    "trigger": trigger
                })
                current += timedelta(minutes=interval_minutes)

        return jobs

    def _build_monthly_jobs(self, schedule: SyncSchedule) -> List[Dict[str, Any]]:
        """Build monthly recurring jobs."""
        jobs = []
        tz = schedule.timezone

        if not schedule.monthly_runs:
            return jobs

        for i, run in enumerate(schedule.monthly_runs):
            day = run["day"]
            hour, minute = parse_time_to_hour_minute(run["time"])

            # Handle "last" day of month
            if day == "last":
                day_expr = "last"
            else:
                day_expr = str(day)

            trigger = CronTrigger(
                day=day_expr,
                hour=hour,
                minute=minute,
                timezone=tz,
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            jobs.append({
                "id": f"monthly_{i}",
                "trigger": trigger
            })

        return jobs

    def _get_interval_minutes(self, schedule: SyncSchedule) -> Optional[int]:
        """Get interval value in minutes."""
        if not schedule.interval_value or not schedule.interval_unit:
            return None

        if schedule.interval_unit == "minutes":
            return schedule.interval_value
        elif schedule.interval_unit == "hours":
            return schedule.interval_value * 60
        else:
            return None

    # ==========================================================================
    # VALIDATION
    # ==========================================================================

    def validate_frequency(self, frequency: str) -> bool:
        """Validate scheduler frequency."""
        return frequency.lower() in VALID_FREQUENCIES

    # ==========================================================================
    # SYNC SCHEDULING (LEGACY)
    # ==========================================================================

    def schedule_all_syncs(self):
        """Schedule syncs for all data sources with frequency settings (legacy)."""
        from fastapi_app.services.data_integration.data_source_service import get_all_data_sources

        db = SessionLocal()
        try:
            data_sources = get_all_data_sources(db)
            for ds in data_sources:
                if ds.sync_frequency and ds.sync_frequency != "manual":
                    if self.validate_frequency(ds.sync_frequency):
                        self.schedule_sync(ds.id, ds.sync_frequency)
                        logger.debug(f"Scheduled sync for data source {ds.id} with frequency {ds.sync_frequency}")
        except Exception as e:
            logger.error(f"Error scheduling all syncs: {str(e)}")
        finally:
            db.close()

    def schedule_sync(self, datasource_id: int, frequency: str):
        """Schedule a specific data source sync (legacy)."""
        if not self.validate_frequency(frequency):
            raise ValueError(f"Invalid frequency '{frequency}'. Must be one of: {', '.join(VALID_FREQUENCIES)}")

        trigger = self._parse_frequency(frequency)
        if trigger:
            job_id = f"sync_{datasource_id}"

            if job_id in self.running_tasks:
                self.scheduler.remove_job(job_id)
                del self.running_tasks[job_id]

            self.scheduler.add_job(
                self._sync_job,
                trigger=trigger,
                id=job_id,
                args=[datasource_id],
                replace_existing=True,
                max_instances=1
            )
            self.running_tasks[job_id] = datasource_id
            logger.debug(f"Scheduled sync job {job_id} with frequency {frequency}")

    def remove_sync(self, datasource_id: int):
        """Remove scheduled sync for a data source (legacy)."""
        job_id = f"sync_{datasource_id}"
        if job_id in self.running_tasks:
            self.scheduler.remove_job(job_id)
            del self.running_tasks[job_id]
            logger.debug(f"Removed scheduled sync for data source {datasource_id}")

    async def _sync_job(self, datasource_id: int):
        """Job to sync a data source."""
        from fastapi_app.services.data_integration.data_source_service import get_data_source
        from fastapi_app.services.data_integration.sync_job_service import SyncJobService
        from fastapi_app.services.background.task_manager import TaskManager

        logger.info(f"Starting scheduled sync for data source {datasource_id}")
        db = SessionLocal()
        try:
            ds = get_data_source(db, datasource_id)
            if not ds:
                logger.warning(f"Data source {datasource_id} no longer exists, removing job")
                self.remove_sync(datasource_id)
                return

            # Create sync job
            job = SyncJobService.create_job(db, datasource_id, triggered_by="scheduled")

            # Run via Celery
            TaskManager.run_sync_job(job.job_id)

            logger.info(f"Created sync job {job.job_id} for scheduled sync of {datasource_id}")
        except Exception as e:
            logger.error(f"Error in sync job for {datasource_id}: {str(e)}")
        finally:
            db.close()

    # ==========================================================================
    # TRAINING SCHEDULING (LEGACY)
    # ==========================================================================

    def schedule_training(self, config_id: int, frequency: str, cron_expression: str = None):
        """Schedule a recurring retraining job."""
        if frequency == "manual":
            self.remove_training(config_id)
            return
            
        trigger = self._parse_frequency(frequency, cron_expression)
        if trigger:
            job_id = f"retrain_{config_id}"
            
            # Remove existing job if any
            if job_id in self.running_tasks:
                try:
                    self.scheduler.remove_job(job_id)
                except Exception:
                    pass
                del self.running_tasks[job_id]
                
            self.scheduler.add_job(
                self._training_job,
                trigger=trigger,
                id=job_id,
                args=[config_id],
                replace_existing=True,
                max_instances=1
            )
            self.running_tasks[job_id] = config_id
            logger.info(f"Scheduled retraining job {job_id} with frequency {frequency}")

    async def _training_job(self, config_id: int):
        """Execute scheduled retraining job."""
        from fastapi_app.services.forecast.training_config_service import TrainingConfigService
        from fastapi_app.services.forecast.model_registry_service import ModelRegistryService
        from fastapi_app.services.forecast.training_service import TrainingService
        from fastapi_app.schemas.forecast_schema import TrainingJobCreate
        from fastapi_app.tasks.celery_tasks import run_training_job_task
        
        logger.info(f"Starting scheduled training job for configuration {config_id}")
        db = SessionLocal()
        try:
            config = TrainingConfigService.get_config(db, config_id)
            if not config or not config.enabled:
                logger.warning(f"Retraining config {config_id} is disabled or deleted. Skipping run.")
                return
                
            model = ModelRegistryService.get_model(db, config.model_registry_id)
            if not model:
                logger.warning(f"Model {config.model_registry_id} not found in registry. Skipping run.")
                return
                
            # Find latest completed processed dataset
            from fastapi_app.models.processing_job_model import ProcessedDataset, ProcessingJob
            latest_processed = db.query(ProcessedDataset).join(
                ProcessingJob, ProcessedDataset.processing_job_id == ProcessingJob.id
            ).filter(
                ProcessingJob.status == "completed"
            ).order_by(ProcessedDataset.created_at.desc()).first()
            
            if not latest_processed:
                logger.warning(f"No completed processed dataset found to run scheduled retraining for model {config.model_registry_id}")
                return
                
            # Create training job
            job_create = TrainingJobCreate(
                model_type=model.model_type,
                model_registry_id=config.model_registry_id,
                processing_job_id=str(latest_processed.processing_job_id),
                epochs=config.epochs or 20,
                batch_size=config.batch_size or 16,
                learning_rate=config.learning_rate or 0.001,
                configuration={}
            )
            
            job = TrainingService.create_job(db, job_create, created_by=None)
            
            # Trigger Celery
            run_training_job_task.delay(job.job_id)
            logger.info(f"Created training job {job.job_id} for scheduled retraining config {config_id}")
        except Exception as e:
            logger.error(f"Error executing scheduled retraining config {config_id}: {str(e)}")
        finally:
            db.close()

    def schedule_all_trainings(self):
        """Schedule retraining for all active configurations."""
        from fastapi_app.models.training_configuration_model import TrainingConfiguration
        db = SessionLocal()
        try:
            configs = db.query(TrainingConfiguration).filter(
                TrainingConfiguration.enabled == True
            ).all()
            for config in configs:
                if config.frequency and config.frequency != "manual":
                    self.schedule_training(config.id, config.frequency, config.cron_expression)
        except Exception as e:
            logger.error(f"Error scheduling all retraining runs: {str(e)}")
        finally:
            db.close()

    def remove_training(self, config_id: int):
        """Remove scheduled retraining job."""
        job_id = f"retrain_{config_id}"
        if job_id in self.running_tasks:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass
            del self.running_tasks[job_id]
            logger.info(f"Removed scheduled retraining config {config_id}")

    def schedule_one_shot_retraining(self, model_registry_id: str, run_at: datetime):
        """Schedule retraining for a specific model registry ID to run only once at run_at."""
        from apscheduler.triggers.date import DateTrigger
        
        # Internal async wrapper that triggers Celery task
        async def _run_once_job(model_id: str):
            from fastapi_app.services.forecast.model_registry_service import ModelRegistryService
            from fastapi_app.services.forecast.training_service import TrainingService
            from fastapi_app.schemas.forecast_schema import TrainingJobCreate
            from fastapi_app.tasks.celery_tasks import run_training_job_task
            
            logger.info(f"Running one-shot retraining job for model {model_id}")
            db = SessionLocal()
            try:
                model = ModelRegistryService.get_model(db, model_id)
                if not model:
                    logger.warning(f"Model {model_id} not found in registry. Skipping one-shot run.")
                    return
                    
                # Find latest completed processed dataset
                from fastapi_app.models.processing_job_model import ProcessedDataset, ProcessingJob
                latest_processed = db.query(ProcessedDataset).join(
                    ProcessingJob, ProcessedDataset.processing_job_id == ProcessingJob.id
                ).filter(
                    ProcessingJob.status == "completed"
                ).order_by(ProcessedDataset.created_at.desc()).first()
                
                if not latest_processed:
                    logger.warning(f"No completed processed dataset found to run one-shot retraining for model {model_id}")
                    return
                    
                # Find configuration defaults if any
                from fastapi_app.models.training_configuration_model import TrainingConfiguration
                config = db.query(TrainingConfiguration).filter(
                    TrainingConfiguration.model_registry_id == model_id
                ).first()
                
                epochs = config.epochs if config else 20
                batch_size = config.batch_size if config else 16
                learning_rate = config.learning_rate if config else 0.001
                
                # Create training job
                job_create = TrainingJobCreate(
                    model_type=model.model_type,
                    model_registry_id=model_id,
                    processing_job_id=str(latest_processed.processing_job_id),
                    epochs=epochs,
                    batch_size=batch_size,
                    learning_rate=learning_rate,
                    configuration={}
                )
                
                job = TrainingService.create_job(db, job_create, created_by=None)
                
                # Trigger Celery
                run_training_job_task.delay(job.job_id)
                logger.info(f"Created one-shot training job {job.job_id} for model {model_id}")
            except Exception as e:
                logger.error(f"Error executing one-shot retraining for model {model_id}: {str(e)}")
            finally:
                db.close()
                
        job_id = f"retrain_once_{model_registry_id}"
        
        # Add date trigger to scheduler
        self.scheduler.add_job(
            _run_once_job,
            trigger=DateTrigger(run_date=run_at),
            id=job_id,
            args=[model_registry_id],
            replace_existing=True
        )
        logger.info(f"Scheduled one-shot retraining {job_id} at {run_at}")

    # ==========================================================================
    # JOB MANAGEMENT
    # ==========================================================================

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "status": "active" if job.next_run_time else "paused"
            })
        return jobs

    def get_sync_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled sync jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith("sync_") or job.id.startswith("schedule_"):
                jobs.append({
                    "id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "status": "active" if job.next_run_time else "paused"
                })
        return jobs

    def get_training_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled training jobs (disabled)."""
        return []


    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific scheduled job"""
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "status": "active" if job.next_run_time else "paused"
            }
        return None

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job {job_id}")
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused scheduled job"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job {job_id}")
            return True
        return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.remove_job(job_id)
            if job_id in self.running_tasks:
                del self.running_tasks[job_id]
            logger.info(f"Removed job {job_id}")
            return True
        return False

    def run_now(self, job_id: str) -> bool:
        """Execute a scheduled job immediately"""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now(self.scheduler.timezone) + timedelta(seconds=1))
            logger.info(f"Triggered job {job_id} to run now")
            return True
        return False

    # ==========================================================================
    # FREQUENCY PARSING
    # ==========================================================================

    def _parse_frequency(self, frequency: str, cron_expression: str = None):
        """Parse frequency string to trigger with cron support."""
        if cron_expression:
            return CronTrigger.from_crontab(cron_expression)

        frequency_map = {
            "manual": None,
            "hourly": IntervalTrigger(hours=1),
            "daily": CronTrigger(hour=0, minute=0),
            "weekly": CronTrigger(day_of_week='mon', hour=0, minute=0),
            "monthly": CronTrigger(day=1, hour=0, minute=0),
            "realtime": IntervalTrigger(minutes=5)
        }
        return frequency_map.get(frequency.lower())


# Global scheduler instance
scheduler = SchedulerService()