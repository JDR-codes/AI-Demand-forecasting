# fastapi_app/services/scheduler/scheduler_service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime

from fastapi_app.db.session import SessionLocal

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running_tasks = {}
        
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            self.schedule_all_syncs()
            
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def schedule_all_syncs(self):
        """Schedule syncs for all data sources with frequency settings"""
        # Import here to avoid circular import
        from fastapi_app.services.data_integration.data_source_service import get_all_data_sources
        
        db = SessionLocal()
        try:
            data_sources = get_all_data_sources(db)
            for ds in data_sources:
                if ds.sync_frequency and ds.sync_frequency != "manual":
                    self.schedule_sync(ds.id, ds.sync_frequency)
                    logger.info(f"Scheduled sync for data source {ds.id} with frequency {ds.sync_frequency}")
        except Exception as e:
            logger.error(f"Error scheduling all syncs: {str(e)}")
        finally:
            db.close()
    
    def schedule_sync(self, datasource_id: int, frequency: str):
        """Schedule a specific data source sync"""
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
            logger.info(f"Scheduled job {job_id} with frequency {frequency}")
        else:
            logger.warning(f"No trigger for frequency: {frequency}")
    
    def _parse_frequency(self, frequency: str):
        """Parse frequency string to trigger"""
        frequency_map = {
            "manual": None,
            "hourly": IntervalTrigger(hours=1),
            "daily": CronTrigger(hour=0, minute=0),  # Every day at midnight
            "weekly": CronTrigger(day_of_week='mon', hour=0, minute=0),  # Every Monday at midnight
            "monthly": CronTrigger(day=1, hour=0, minute=0),  # First day of month at midnight - FIXED
            "realtime": IntervalTrigger(minutes=5)
        }
        return frequency_map.get(frequency.lower())
    
    async def _sync_job(self, datasource_id: int):
        """Job to sync a data source"""
        # Import here to avoid circular import
        from fastapi_app.services.data_integration.data_source_service import sync_data_source, get_data_source
        
        logger.info(f"Starting scheduled sync for data source {datasource_id}")
        db = SessionLocal()
        try:
            # Check if data source still exists and is scheduled
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
    
    def remove_sync(self, datasource_id: int):
        """Remove scheduled sync for a data source"""
        job_id = f"sync_{datasource_id}"
        if job_id in self.running_tasks:
            self.scheduler.remove_job(job_id)
            del self.running_tasks[job_id]
            logger.info(f"Removed scheduled sync for data source {datasource_id}")
        else:
            logger.info(f"No scheduled job found for data source {datasource_id}")
    
    def get_scheduled_jobs(self):
        """Get all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs
    
    def get_job_status(self, datasource_id: int):
        """Get status of a specific scheduled job"""
        job_id = f"sync_{datasource_id}"
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
        return None

# Global scheduler instance
scheduler = SchedulerService()