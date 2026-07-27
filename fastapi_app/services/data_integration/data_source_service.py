#fastapi_app/data_integration/data_source_service.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import logging
import json
import time

from fastapi_app.schemas.data_source_dashboard_schema import DataSourceDashboardMetrics
from fastapi_app.models.data_source_model import DataSource, DataSourceType
from fastapi_app.models.sync_log_model import SyncLog
from fastapi_app.services.scheduler.scheduler_service import scheduler
from fastapi_app.models.raw_data_model import RawSales, RawInventory, RawSupplier, RawProducts
from fastapi_app.models.validation_error_model import ValidationError
from fastapi_app.services.connectors import (
    fetch_api,
    fetch_csv,
    fetch_mysql_table,
    fetch_sqlite_table
)
from fastapi_app.services.validation.validation_service import ValidationEngine
from fastapi_app.services.validation.validation_service import create_validation_error
from fastapi_app.services.notifications.notification_service import NotificationService
from fastapi_app.models.auth_model import User
from fastapi_app.services.data_integration.test_connection_service import TestConnectionService

logger = logging.getLogger(__name__)

# ============================================================================
# CRUD OPERATIONS
# ============================================================================

def get_all_data_sources(db: Session) -> List[DataSource]:
    """Get all data sources"""
    return db.query(DataSource).all()

def get_data_source(db: Session, data_source_id: int) -> Optional[DataSource]:
    """Get a single data source by ID"""
    return db.query(DataSource).filter(DataSource.id == data_source_id).first()

def create_data_source(db: Session, data: Dict[str, Any]) -> DataSource:
    """Create a new data source"""
    ds = DataSource(**data)
    db.add(ds)
    db.commit()
    db.refresh(ds)
    
    # Auto-test connection to record initial test history
    try:
        TestConnectionService.test_connection_with_history(db, ds)
    except Exception as e:
        logger.warning(f"Initial connection test failed for data source {ds.id}: {e}")
        
    return ds

def update_data_source(db: Session, data_source_id: int, data: Dict[str, Any]) -> Optional[DataSource]:
    """Update an existing data source"""
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    for key, value in data.items():
        if value is not None and hasattr(ds, key):
            setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return ds

def delete_data_source(db: Session, data_source_id: int) -> bool:
    """Delete a data source"""
    ds = get_data_source(db, data_source_id)
    if not ds:
        return False
    db.delete(ds)
    db.commit()
    return True

def test_connection(db: Session, data_source_id: int) -> Dict[str, Any]:
    """Test connection for a data source."""
    ds = get_data_source(db, data_source_id)
    if not ds:
        return {"success": False, "message": "Data source not found"}
    
    return TestConnectionService.test_connection_with_history(db, ds)

def schedule_sync_data_source(db: Session, data_source_id: int, frequency: str = None) -> Optional[DataSource]:
    """Schedule a data source sync with the scheduler."""
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    
    if frequency:
        ds.sync_frequency = frequency
    
    ds.status = "scheduled"
    db.commit()
    db.refresh(ds)
    
    if ds.sync_frequency and ds.sync_frequency != "manual":
        scheduler.schedule_sync(ds.id, ds.sync_frequency)
        logger.info(f"Scheduled sync for data source {ds.id} with frequency {ds.sync_frequency}")
    else:
        scheduler.remove_sync(ds.id)
        logger.info(f"Removed sync schedule for data source {ds.id}")
    
    return ds

def get_data_source_health(db: Session, data_source_id: int) -> Optional[Dict[str, Any]]:
    """Get health information for a data source"""
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    
    health_score = 100
    if ds.status == "failed":
        health_score -= 40
    if ds.status == "error":
        health_score -= 30
    if ds.health == "unhealthy":
        health_score -= 20
    
    return {
        "health": ds.health,
        "health_score": max(0, health_score),
        "status": ds.status,
        "last_sync": ds.last_sync,
        "sync_frequency": ds.sync_frequency
    }

def get_data_source_logs(db: Session, data_source_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Get logs for a data source from both SyncJob and SyncLog."""
    from fastapi_app.models.sync_job_model import SyncJob
    
    ds = get_data_source(db, data_source_id)
    if not ds:
        return []
    
    logs_list = []
    
    # 1. Fetch SyncJob records
    sync_jobs = db.query(SyncJob).filter(
        SyncJob.datasource_id == data_source_id
    ).order_by(SyncJob.created_at.desc()).limit(limit).all()
    
    for job in sync_jobs:
        status_val = job.status.value if hasattr(job.status, "value") else str(job.status)
        msg = f"Synced {job.rows_processed} rows successfully." if status_val == "completed" else (job.error_message or f"Sync job {status_val}")
        logs_list.append({
            "timestamp": job.started_at or job.created_at,
            "status": status_val,
            "rows_processed": job.rows_processed or 0,
            "duration_seconds": job.duration_seconds,
            "message": msg
        })
    
    # 2. Fetch SyncLog records
    sync_logs = db.query(SyncLog).filter(
        SyncLog.datasource_id == data_source_id
    ).order_by(SyncLog.started_at.desc()).limit(limit).all()
    
    for log in sync_logs:
        logs_list.append({
            "timestamp": log.started_at,
            "status": log.status,
            "rows_processed": log.rows_processed or 0,
            "duration_seconds": log.duration_seconds,
            "message": log.message or f"Sync {log.status}"
        })
        
    # Sort combined logs by timestamp descending and take limit
    logs_list.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
    return logs_list[:limit]

# ============================================================================
# DASHBOARD METRICS
# ============================================================================

def get_data_source_dashboard_metrics(db: Session) -> DataSourceDashboardMetrics:
    """Get dashboard metrics for data sources."""
    
    total_records = 0
    raw_tables = [RawSales, RawInventory, RawSupplier, RawProducts]
    for table in raw_tables:
        count = db.query(func.count(table.id)).scalar() or 0
        total_records += count
    
    active_connections = db.query(DataSource).filter(
        DataSource.status.in_(["success", "syncing", "active", "connected"])
    ).count()
    
    total_connections = db.query(DataSource).count()
    sync_frequency = get_sync_frequency_summary(db)
    validation_errors = db.query(ValidationError).filter(
        ValidationError.status == "open"
    ).count()
    
    return DataSourceDashboardMetrics(
        total_records=total_records,
        active_connections=active_connections,
        total_connections=total_connections,
        sync_frequency=sync_frequency,
        validation_errors=validation_errors
    )

def get_sync_frequency_summary(db: Session) -> str:
    """Calculate the sync frequency summary."""
    sources = db.query(DataSource).all()
    
    if not sources:
        return "N/A"
    
    realtime_count = db.query(DataSource).filter(
        DataSource.sync_frequency == "realtime"
    ).count()
    
    if realtime_count > 0:
        return "<5 min"
    
    hourly_count = db.query(DataSource).filter(
        DataSource.sync_frequency == "hourly"
    ).count()
    
    if hourly_count > 0:
        return "~1 hour"
    
    frequency_counts = {}
    for source in sources:
        freq = source.sync_frequency or "manual"
        frequency_counts[freq] = frequency_counts.get(freq, 0) + 1
    
    if frequency_counts:
        most_common = max(frequency_counts, key=frequency_counts.get)
        
        frequency_display = {
            "manual": "Manual",
            "daily": "Daily",
            "weekly": "Weekly",
            "monthly": "Monthly",
            "hourly": "~1 hour",
            "realtime": "<5 min"
        }
        
        return frequency_display.get(most_common, most_common)
    
    return "N/A"

# ============================================================================
# SYNC OPERATIONS
# ============================================================================

def sync_data_source(db: Session, data_source_id: int, triggered_by: str = "manual") -> Optional[DataSource]:
    """Sync data from a data source with full transaction support."""
    from sqlalchemy.exc import SQLAlchemyError
    
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    
    sync_log = SyncLog(
        datasource_id=ds.id,
        status="running",
        started_at=datetime.utcnow(),
        triggered_by=triggered_by
    )
    db.add(sync_log)
    db.flush()
    
    ds.status = "syncing"
    ds.health = "unknown"
    db.flush()
    
    start_time = time.time()
    error_count = 0
    
    validation_errors_batch = []
    
    try:
        data = fetch_data_from_source(ds)
        sync_log.rows_processed = len(data) if data else 0
        
        if not data:
            sync_log.status = "failed"
            sync_log.message = "No data retrieved"
            ds.status = "failed"
            ds.health = "unhealthy"
            
            admin_users = db.query(User).filter(User.is_admin == True).all()
            for admin in admin_users:
                NotificationService.create_sync_notification(
                    db=db,
                    user_id=admin.id,
                    datasource_name=ds.name,
                    success=False,
                    message=f"Data source '{ds.name}' sync failed: No data retrieved"
                )
        else:
            df = pd.DataFrame(data)
            
            source_type = get_source_type_name(ds.provider)
            df = ValidationEngine.standardize_dataframe(df, source_type)
            
            is_valid, errors, stats = ValidationEngine.validate_dataframe(
                df, source_type, ds.name
            )
            
            for error in errors:
                validation_errors_batch.append({
                    "source": f"datasource:{ds.id}",
                    "error_type": error.get('column_name', 'unknown'),
                    "severity": error.get('severity', 'medium'),
                    "rows_affected": error.get('row_number', 0),
                    "status": "open",
                    "column_name": error.get('column_name'),
                    "row_number": error.get('row_number', 0),
                    "expected_value": error.get('expected_value', ''),
                    "actual_value": error.get('actual_value', ''),
                    "error_message": error.get('error_message', ''),
                    "suggestion": error.get('suggestion', ''),
                    "datasource_id": ds.id,
                    "sync_id": sync_log.id
                })
            
            if validation_errors_batch:
                for error_data in validation_errors_batch:
                    create_validation_error(
                        db,
                        source=error_data["source"],
                        error_type=error_data["error_type"],
                        severity=error_data["severity"],
                        rows_affected=error_data["rows_affected"],
                        status=error_data["status"],
                        column_name=error_data["column_name"],
                        row_number=error_data["row_number"],
                        expected_value=error_data["expected_value"],
                        actual_value=error_data["actual_value"],
                        error_message=error_data["error_message"],
                        suggestion=error_data["suggestion"],
                        datasource_id=error_data["datasource_id"],
                        sync_id=error_data["sync_id"]
                    )
                db.commit()
            
            if is_valid or len(errors) < len(df) * 0.5:
                store_raw_data_batch(db, df, ds.id, sync_log.id, source_type)
                
                health_score = calculate_health_score(db, ds.id)
                ds.health = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy"
                ds.status = "success" if is_valid else "partial_success"
                sync_log.status = "success" if is_valid else "partial_success"
                sync_log.rows_validated = len(df) - len(errors)
                
                admin_users = db.query(User).filter(User.is_admin == True).all()
                for admin in admin_users:
                    NotificationService.create_sync_notification(
                        db=db,
                        user_id=admin.id,
                        datasource_name=ds.name,
                        success=True,
                        message=f"Data source '{ds.name}' synced successfully. {len(data)} records processed."
                    )
            else:
                ds.status = "failed"
                ds.health = "unhealthy"
                sync_log.status = "failed"
                sync_log.message = f"Validation failed with {len(errors)} errors"
                
                admin_users = db.query(User).filter(User.is_admin == True).all()
                for admin in admin_users:
                    NotificationService.create_sync_notification(
                        db=db,
                        user_id=admin.id,
                        datasource_name=ds.name,
                        success=False,
                        message=f"Data source '{ds.name}' sync failed: Validation failed with {len(errors)} errors"
                    )
            
            sync_log.rows_failed = len(errors)
            ds.last_sync = datetime.utcnow()
        
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = time.time() - start_time
        
        db.commit()
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error syncing data source {ds.id}: {str(e)}")
        ds.status = "failed"
        ds.health = "error"
        sync_log.status = "failed"
        sync_log.message = f"Database error: {str(e)}"
        sync_log.error_details = str(e)
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = time.time() - start_time
        db.commit()
        
        admin_users = db.query(User).filter(User.is_admin == True).all()
        for admin in admin_users:
            NotificationService.create_sync_notification(
                db=db,
                user_id=admin.id,
                datasource_name=ds.name,
                success=False,
                message=f"Data source '{ds.name}' sync failed: Database error - {str(e)}"
            )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error syncing data source {ds.id}: {str(e)}")
        ds.status = "failed"
        ds.health = "error"
        sync_log.status = "failed"
        sync_log.message = f"Sync failed: {str(e)}"
        sync_log.error_details = str(e)
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = time.time() - start_time
        db.commit()
        
        admin_users = db.query(User).filter(User.is_admin == True).all()
        for admin in admin_users:
            NotificationService.create_sync_notification(
                db=db,
                user_id=admin.id,
                datasource_name=ds.name,
                success=False,
                message=f"Data source '{ds.name}' sync failed: {str(e)}"
            )
    
    db.refresh(ds)
    return ds

def calculate_health_score(db: Session, datasource_id: int) -> float:
    """Calculate health score based on last 10 syncs."""
    recent_syncs = db.query(SyncLog).filter(
        SyncLog.datasource_id == datasource_id
    ).order_by(SyncLog.started_at.desc()).limit(10).all()
    
    if not recent_syncs:
        return 100.0
    
    total_syncs = len(recent_syncs)
    successful_syncs = sum(1 for s in recent_syncs if s.status == "success")
    total_duration = sum(s.duration_seconds or 0 for s in recent_syncs)
    avg_duration = total_duration / total_syncs if total_syncs > 0 else 0
    
    success_rate = (successful_syncs / total_syncs) * 100
    duration_score = max(0, 100 - (avg_duration / 10))
    
    health_score = (success_rate * 0.7) + (duration_score * 0.3)
    
    return min(100, health_score)

def fetch_data_from_source(ds: DataSource) -> Optional[List[Dict[str, Any]]]:
    """Fetch data based on data source type."""
    try:
        if ds.type == DataSourceType.API:
            if not ds.base_url:
                raise ValueError("API data source requires base_url")
            
            headers = {}
            if ds.api_key:
                headers['Authorization'] = f'Bearer {ds.api_key}'
            
            if ds.provider == "SUPPLIER":
                headers['X-Supplier-API-Version'] = 'v2'
            
            return fetch_api(ds.base_url, headers=headers)
            
        elif ds.type == DataSourceType.DATABASE:
            if not ds.connection_string:
                raise ValueError("Database data source requires connection_string")
            
            table_name = ds.table_name
            if not table_name:
                provider_table_map = {
                    "SAP": "sales",
                    "MYSQL": "sales",
                    "POSTGRES": "sales",
                    "SQLITE": "sales"
                }
                table_name = provider_table_map.get(str(ds.provider), "sales")
            
            if ds.provider == "MYSQL":
                return fetch_mysql_table(ds.connection_string, table_name)
            elif ds.provider == "SQLITE":
                return fetch_sqlite_table(ds.connection_string, table_name)
            else:
                raise ValueError(f"Unsupported database provider: {ds.provider}")
                
        elif ds.type == DataSourceType.LOCAL_FOLDER:
            if not ds.folder_path:
                raise ValueError("Folder data source requires folder_path")
            
            if ds.folder_path.lower().endswith('.csv'):
                return fetch_csv(ds.folder_path)
            else:
                from fastapi_app.services.connectors.folder_connector import fetch_all_csvs_in_folder
                result = fetch_all_csvs_in_folder(ds.folder_path)
                all_data = []
                for file_data in result.values():
                    all_data.extend(file_data)
                return all_data
                
        elif ds.type == DataSourceType.CLOUD_STORAGE:
            raise NotImplementedError("Cloud storage connector not yet implemented")
            
        else:
            raise ValueError(f"Unsupported data source type: {ds.type}")
            
    except Exception as e:
        logger.error(f"Error fetching from data source {ds.id}: {str(e)}")
        raise

def get_source_type_name(provider: str) -> str:
    """Map provider to source type for validation"""
    type_map = {
        "SALES": "sales",
        "SUPPLIER": "supplier",
        "INVENTORY": "inventory",
        "PRODUCTS": "products"
    }
    return type_map.get(str(provider).upper(), "api")

def store_raw_data_batch(db: Session, df: pd.DataFrame, datasource_id: int, 
                         sync_log_id: int, source_type: str, batch_size: int = 1000) -> None:
    """Store validated data in appropriate raw tables using BATCH operations."""
    records = df.to_dict('records')
    
    model_map = {
        "sales": RawSales,
        "inventory": RawInventory,
        "supplier": RawSupplier,
        "products": RawProducts
    }
    
    model_class = model_map.get(source_type)
    if not model_class:
        model_class = RawSales
    
    field_mapping = {
        "sales": {
            "date": "date",
            "demand": "demand",
            "revenue": "revenue",
            "units": "units",
            "sku": "sku"
        },
        "inventory": {
            "warehouse": "warehouse",
            "stock": "stock",
            "reorder_level": "reorder_level",
            "last_updated": "last_updated",
            "sku": "sku"
        },
        "supplier": {
            "supplier": "supplier",
            "lead_time": "lead_time",
            "price": "price",
            "min_order": "min_order",
            "sku": "sku"
        },
        "products": {
            "name": "name",
            "category": "category",
            "price": "price",
            "sku": "sku"
        }
    }
    
    mapping = field_mapping.get(source_type, {})
    
    objects_to_add = []
    total_objects = 0
    
    for record in records:
        mapped_data = {}
        for source_field, target_field in mapping.items():
            if source_field in record:
                mapped_data[target_field] = record[source_field]
        
        mapped_data['datasource_id'] = datasource_id
        mapped_data['sync_id'] = sync_log_id
        
        raw_record = {}
        for key, value in record.items():
            if hasattr(value, 'to_pydatetime'):
                raw_record[key] = value.isoformat()
            elif hasattr(value, 'tolist'):
                raw_record[key] = value.tolist()
            elif hasattr(value, 'item'):
                raw_record[key] = value.item()
            else:
                raw_record[key] = value
        
        mapped_data['raw_data'] = raw_record
        mapped_data['validation_status'] = "validated"
        
        try:
            obj = model_class(**mapped_data)
            objects_to_add.append(obj)
            total_objects += 1
            
            if len(objects_to_add) >= batch_size:
                db.add_all(objects_to_add)
                db.commit()
                logger.debug(f"Stored batch of {len(objects_to_add)} records")
                objects_to_add = []
                
        except Exception as e:
            logger.error(f"Error storing raw data: {str(e)}")
            continue
    
    if objects_to_add:
        db.add_all(objects_to_add)
        db.commit()
        logger.debug(f"Stored final batch of {len(objects_to_add)} records")
    
    logger.info(f"Stored {total_objects} records in {source_type} table")

def store_raw_data(db: Session, df: pd.DataFrame, datasource_id: int, 
                   sync_log_id: int, source_type: str) -> None:
    """Legacy wrapper for store_raw_data_batch."""
    return store_raw_data_batch(db, df, datasource_id, sync_log_id, source_type)

def create_validation_errors_batch(
    db: Session,
    errors: List[Dict[str, Any]],
    datasource_id: int,
    sync_id: int
) -> None:
    """Create multiple validation errors in a single batch operation."""
    from fastapi_app.models.validation_error_model import ValidationError
    
    if not errors:
        return
    
    error_objects = []
    for error in errors:
        err = ValidationError(
            source=f"datasource:{datasource_id}",
            error_type=error.get('column_name', 'unknown'),
            severity=error.get('severity', 'medium'),
            rows_affected=error.get('row_number', 0),
            status="open",
            column_name=error.get('column_name'),
            row_number=error.get('row_number', 0),
            expected_value=error.get('expected_value', ''),
            actual_value=error.get('actual_value', ''),
            error_message=error.get('error_message', ''),
            suggestion=error.get('suggestion', ''),
            datasource_id=datasource_id,
            sync_id=sync_id
        )
        error_objects.append(err)
    
    if error_objects:
        db.bulk_save_objects(error_objects)
        db.commit()
        logger.debug(f"Stored {len(error_objects)} validation errors")