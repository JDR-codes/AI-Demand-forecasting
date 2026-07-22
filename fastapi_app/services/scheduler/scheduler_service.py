# fastapi_app/services/scheduler/scheduler_service.py
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Valid frequencies for validation
VALID_FREQUENCIES = ["manual", "hourly", "daily", "weekly", "monthly", "realtime"]


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running_tasks = {}
        
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            try:
                # Try to get existing loop or create new one
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                self.scheduler.start()
                logger.info("Scheduler started")
                
                # Schedule jobs after start
                self.schedule_all_syncs()
                self.schedule_all_trainings()
                
                # Schedule inventory tasks
                self.schedule_inventory_tasks()
                
            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")
            
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    # ==========================================================================
    # INVENTORY TASKS
    # ==========================================================================
    
    def schedule_inventory_tasks(self):
        """Schedule all inventory-related tasks."""
        # Nightly inventory tasks (runs at 2 AM every day)
        self.scheduler.add_job(
            self._run_nightly_inventory_tasks,
            trigger=CronTrigger(hour=2, minute=0),
            id="inventory_nightly",
            replace_existing=True,
            max_instances=1
        )
        logger.info("Scheduled nightly inventory tasks at 2 AM")
        
        # Hourly inventory checks (runs every hour)
        self.scheduler.add_job(
            self._run_hourly_inventory_tasks,
            trigger=IntervalTrigger(hours=1),
            id="inventory_hourly",
            replace_existing=True,
            max_instances=1
        )
        logger.info("Scheduled hourly inventory checks")
        
        # Dashboard cache refresh (every 15 minutes)
        self.scheduler.add_job(
            self._refresh_dashboard_cache,
            trigger=IntervalTrigger(minutes=15),
            id="dashboard_cache_refresh",
            replace_existing=True,
            max_instances=1
        )
        logger.info("Scheduled dashboard cache refresh every 15 minutes")
    
    async def _run_nightly_inventory_tasks(self):
        """Run all nightly inventory tasks."""
        logger.info("Starting nightly inventory tasks...")
        db = SessionLocal()
        
        try:
            from fastapi_app.models.inventory_model import WarehouseInventory
            from fastapi_app.services.inventory.inventory_service import InventoryService
            from fastapi_app.services.inventory.excess_stock_service import ExcessStockService
            from fastapi_app.services.inventory.slow_moving_service import SlowMovingService
            from fastapi_app.services.inventory.transfer_optimization_service import TransferOptimizationService
            from fastapi_app.services.inventory.alert_service import AlertService
            from fastapi_app.services.inventory.dashboard_cache_service import DashboardCacheService
            
            # 1. Update inventory values
            logger.info("Updating inventory values...")
            InventoryService.update_inventory_value(db)
            
            # 2. Run safety stock calculations
            logger.info("Running safety stock calculations...")
            all_skus = db.query(WarehouseInventory.sku).distinct().all()
            sku_list = [s[0] for s in all_skus]
            InventoryService.get_safety_stock_report(db, 95)
            
            # 3. Run reorder calculations
            logger.info("Running reorder calculations...")
            InventoryService.get_reorder_points_report(db)
            
            # 4. Identify excess stock
            logger.info("Identifying excess stock...")
            ExcessStockService.identify_excess_stock(db)
            
            # 5. Identify slow moving items
            logger.info("Identifying slow moving items...")
            SlowMovingService.get_slow_moving_items(db)
            
            # 6. Generate transfer recommendations
            logger.info("Generating transfer recommendations...")
            TransferOptimizationService.generate_transfer_recommendations(db)
            
            # 7. Run alert check
            logger.info("Running alert check...")
            AlertService.run_complete_alert_check(db)
            
            # 8. Invalidate and refresh dashboard cache
            logger.info("Refreshing dashboard cache...")
            DashboardCacheService.invalidate_cache()
            
            logger.info("Nightly inventory tasks completed successfully")
            
        except Exception as e:
            logger.error(f"Nightly inventory tasks failed: {str(e)}")
        finally:
            db.close()
    
    async def _run_hourly_inventory_tasks(self):
        """Run hourly inventory tasks."""
        logger.info("Starting hourly inventory tasks...")
        db = SessionLocal()
        
        try:
            from fastapi_app.services.inventory.alert_service import AlertService
            from fastapi_app.services.inventory.dashboard_cache_service import DashboardCacheService
            
            # Check for critical alerts
            AlertService.run_complete_alert_check(db)
            
            # Refresh dashboard cache
            DashboardCacheService.invalidate_cache()
            
            logger.info("Hourly inventory tasks completed")
            
        except Exception as e:
            logger.error(f"Hourly inventory tasks failed: {str(e)}")
        finally:
            db.close()
    
    async def _refresh_dashboard_cache(self):
        """Refresh dashboard cache."""
        try:
            from fastapi_app.services.inventory.dashboard_cache_service import DashboardCacheService
            db = SessionLocal()
            try:
                # This will regenerate the cache
                DashboardCacheService.get_dashboard_data(db)
                logger.info("Dashboard cache refreshed")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to refresh dashboard cache: {str(e)}")
    
    # ==========================================================================
    # VALIDATION
    # ==========================================================================
    
    def validate_frequency(self, frequency: str) -> bool:
        """Validate scheduler frequency."""
        return frequency.lower() in VALID_FREQUENCIES
    
    # ==========================================================================
    # SYNC SCHEDULING
    # ==========================================================================
    
    def schedule_all_syncs(self):
        """Schedule syncs for all data sources with frequency settings"""
        from fastapi_app.services.data_integration.data_source_service import get_all_data_sources
        
        db = SessionLocal()
        try:
            data_sources = get_all_data_sources(db)
            for ds in data_sources:
                if ds.sync_frequency and ds.sync_frequency != "manual":
                    if self.validate_frequency(ds.sync_frequency):
                        self.schedule_sync(ds.id, ds.sync_frequency)
                        logger.info(f"Scheduled sync for data source {ds.id} with frequency {ds.sync_frequency}")
                    else:
                        logger.warning(f"Invalid frequency '{ds.sync_frequency}' for data source {ds.id}")
        except Exception as e:
            logger.error(f"Error scheduling all syncs: {str(e)}")
        finally:
            db.close()
    
    def schedule_sync(self, datasource_id: int, frequency: str):
        """Schedule a specific data source sync"""
        if not self.validate_frequency(frequency):
            raise ValueError(f"Invalid frequency '{frequency}'. Must be one of: {', '.join(VALID_FREQUENCIES)}")
        
        trigger = self._parse_frequency(frequency)
        if trigger:
            job_id = f"sync_{datasource_id}"
            
            # Remove existing job if it exists
            if job_id in self.running_tasks:
                self.scheduler.remove_job(job_id)
                del self.running_tasks[job_id]
            
            # Add the job
            self.scheduler.add_job(
                self._sync_job,
                trigger=trigger,
                id=job_id,
                args=[datasource_id],
                replace_existing=True,
                max_instances=1
            )
            self.running_tasks[job_id] = datasource_id
            logger.info(f"Scheduled sync job {job_id} with frequency {frequency}")
        else:
            logger.warning(f"No trigger for frequency: {frequency}")
    
    def remove_sync(self, datasource_id: int):
        """Remove scheduled sync for a data source"""
        job_id = f"sync_{datasource_id}"
        if job_id in self.running_tasks:
            self.scheduler.remove_job(job_id)
            del self.running_tasks[job_id]
            logger.info(f"Removed scheduled sync for data source {datasource_id}")
        else:
            logger.info(f"No scheduled sync job found for data source {datasource_id}")
    
    async def _sync_job(self, datasource_id: int):
        """Job to sync a data source"""
        from fastapi_app.services.data_integration.data_source_service import sync_data_source, get_data_source
        
        logger.info(f"Starting scheduled sync for data source {datasource_id}")
        db = SessionLocal()
        try:
            ds = get_data_source(db, datasource_id)
            if not ds:
                logger.warning(f"Data source {datasource_id} no longer exists, removing job")
                self.remove_sync(datasource_id)
                return
            
            if ds.sync_frequency == "manual":
                logger.info(f"Data source {datasource_id} is set to manual, skipping sync")
                return
            
            result = sync_data_source(db, datasource_id, triggered_by="scheduled")
            if result:
                logger.info(f"Completed scheduled sync for data source {datasource_id}")
            else:
                logger.error(f"Failed to sync data source {datasource_id}")
        except Exception as e:
            logger.error(f"Error in sync job for {datasource_id}: {str(e)}")
        finally:
            db.close()
    
    # ==========================================================================
    # TRAINING SCHEDULING
    # ==========================================================================
    
    def schedule_training(self, config_id: int, frequency: str, cron_expression: str = None):
        """Schedule retraining for a model based on configuration."""
        if not self.validate_frequency(frequency):
            raise ValueError(f"Invalid frequency '{frequency}'. Must be one of: {', '.join(VALID_FREQUENCIES)}")
        
        job_id = f"training_{config_id}"
        
        # Remove existing job if it exists
        if job_id in self.running_tasks:
            self.scheduler.remove_job(job_id)
            del self.running_tasks[job_id]
        
        trigger = self._parse_frequency(frequency, cron_expression)
        if trigger:
            self.scheduler.add_job(
                self._training_job,
                trigger=trigger,
                id=job_id,
                args=[config_id],
                replace_existing=True,
                max_instances=1
            )
            self.running_tasks[job_id] = config_id
            logger.info(f"Scheduled training job {job_id} with frequency {frequency}")
        else:
            logger.warning(f"No trigger for frequency: {frequency}")

    async def _training_job(self, config_id: int):
        """Job to run scheduled retraining."""
        from fastapi_app.services.forecast.training_service import TrainingService
        from fastapi_app.services.forecast.training_config_service import TrainingConfigService
        from fastapi_app.services.forecast.model_registry_service import ModelRegistryService
        from fastapi_app.db.session import SessionLocal
        
        logger.info(f"Starting scheduled training for config {config_id}")
        db = SessionLocal()
        try:
            config = TrainingConfigService.get_config(db, config_id)
            if not config or not config.enabled:
                logger.info(f"Training config {config_id} disabled, skipping")
                return
            
            # Check if model registry exists
            if config.model_registry_id:
                model = ModelRegistryService.get_model(db, config.model_registry_id)
                if not model:
                    logger.warning(f"Model {config.model_registry_id} not found, skipping")
                    return
            
            # Create training job
            from fastapi_app.schemas.forecast_schema import TrainingJobCreate
            create_data = TrainingJobCreate(
                model_type=config.model_registry_id or "auto",
                configuration={
                    "epochs": config.epochs,
                    "batch_size": config.batch_size,
                    "learning_rate": config.learning_rate,
                    "validation_split": config.validation_split,
                    "minimum_records": config.minimum_records,
                    "accuracy_threshold": config.accuracy_threshold
                }
            )
            
            # Create and run training job
            job = TrainingService.create_job(db, create_data, None)
            TrainingService.run_job(db, job.job_id)
            
            logger.info(f"Completed scheduled training for config {config_id}, job {job.job_id}")
        except Exception as e:
            logger.error(f"Error in training job for {config_id}: {str(e)}")
        finally:
            db.close()

    def schedule_all_trainings(self):
        """Schedule all enabled training configurations."""
        from fastapi_app.services.forecast.training_config_service import TrainingConfigService
        from fastapi_app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            configs = TrainingConfigService.get_configs(db)
            for config in configs:
                if config.enabled:
                    self.schedule_training(config.id, config.frequency, config.cron_expression)
                    logger.info(f"Scheduled training for config {config.id} with frequency {config.frequency}")
        except Exception as e:
            logger.error(f"Error scheduling all trainings: {str(e)}")
        finally:
            db.close()
    
    def remove_training(self, config_id: int):
        """Remove scheduled training for a config"""
        job_id = f"training_{config_id}"
        if job_id in self.running_tasks:
            self.scheduler.remove_job(job_id)
            del self.running_tasks[job_id]
            logger.info(f"Removed scheduled training for config {config_id}")
        else:
            logger.info(f"No scheduled training job found for config {config_id}")
    
    # ==========================================================================
    # JOB MANAGEMENT
    # ==========================================================================
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            # Determine job type
            if job.id.startswith("sync_"):
                job_type = "sync"
                entity_id = job.id.split("_")[1] if "_" in job.id and len(job.id.split("_")) > 1 else None
            elif job.id.startswith("training_"):
                job_type = "training"
                entity_id = job.id.split("_")[1] if "_" in job.id and len(job.id.split("_")) > 1 else None
            elif job.id == "inventory_nightly":
                job_type = "inventory_nightly"
                entity_id = None
            elif job.id == "inventory_hourly":
                job_type = "inventory_hourly"
                entity_id = None
            elif job.id == "dashboard_cache_refresh":
                job_type = "dashboard_cache"
                entity_id = None
            else:
                job_type = "unknown"
                entity_id = None
            
            jobs.append({
                "id": job.id,
                "type": job_type,
                "entity_id": entity_id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "status": "active" if job.next_run_time else "paused"
            })
        return jobs
    
    def get_sync_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled sync jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith("sync_"):
                datasource_id = job.id.split("_")[1] if "_" in job.id else None
                jobs.append({
                    "id": job.id,
                    "datasource_id": datasource_id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "status": "active" if job.next_run_time else "paused"
                })
        return jobs
    
    def get_training_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled training jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith("training_"):
                config_id = job.id.split("_")[1] if "_" in job.id else None
                jobs.append({
                    "id": job.id,
                    "config_id": config_id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "status": "active" if job.next_run_time else "paused"
                })
        return jobs
    
    def get_inventory_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled inventory jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            if job.id in ["inventory_nightly", "inventory_hourly", "dashboard_cache_refresh"]:
                jobs.append({
                    "id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "status": "active" if job.next_run_time else "paused"
                })
        return jobs
    
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
            from datetime import datetime, timedelta
            job.modify(next_run_time=datetime.utcnow() + timedelta(seconds=1))
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