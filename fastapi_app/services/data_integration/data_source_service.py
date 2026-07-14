# fastapi_app/services/data_integration/data_source_service.py
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
    # fetch_postgres_table,
    fetch_sqlite_table
)
from fastapi_app.services.validation.validation_service import ValidationEngine
from fastapi_app.services.validation.validation_service import create_validation_error

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

def schedule_sync_data_source(db: Session, data_source_id: int, frequency: str = None) -> Optional[DataSource]:
    """
    Schedule a data source sync with the scheduler.
    """
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    
    # If frequency is provided, update it
    if frequency:
        ds.sync_frequency = frequency
    
    # Update status
    ds.status = "scheduled"
    db.commit()
    db.refresh(ds)
    
    # Actually schedule the sync with the scheduler
    if ds.sync_frequency and ds.sync_frequency != "manual":
        scheduler.schedule_sync(ds.id, ds.sync_frequency)
        logger.info(f"Scheduled sync for data source {ds.id} with frequency {ds.sync_frequency}")
    else:
        # Remove from scheduler if frequency is manual
        scheduler.remove_sync(ds.id)
        logger.info(f"Removed sync schedule for data source {ds.id}")
    
    return ds


def get_data_source_health(db: Session, data_source_id: int) -> Optional[Dict[str, Any]]:
    """Get health information for a data source"""
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    
    # Calculate health score
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

def get_data_source_logs(db: Session, data_source_id: int) -> List[Dict[str, Any]]:
    """Get logs for a data source"""
    ds = get_data_source(db, data_source_id)
    if not ds:
        return []
    
    # Get recent sync logs
    logs = db.query(SyncLog).filter(
        SyncLog.datasource_id == data_source_id
    ).order_by(SyncLog.started_at.desc()).limit(10).all()
    
    return [
        {
            "timestamp": log.started_at,
            "status": log.status,
            "rows_processed": log.rows_processed,
            "duration_seconds": log.duration_seconds,
            "message": log.message
        }
        for log in logs
    ]

# ============================================================================
# DASHBOARD METRICS
# ============================================================================

def get_data_source_dashboard_metrics(db: Session) -> DataSourceDashboardMetrics:
    """
    Get dashboard metrics for data sources.
    Returns exactly the format needed for the UI.
    """
    
    # 1. Total Records (sum of all raw data tables)
    total_records = 0
    raw_tables = [RawSales, RawInventory, RawSupplier, RawProducts]
    for table in raw_tables:
        count = db.query(func.count(table.id)).scalar() or 0
        total_records += count
    
    # 2. Active Connections (status is 'success', 'syncing', 'active', or 'connected')
    active_connections = db.query(DataSource).filter(
        DataSource.status.in_(["success", "syncing", "active", "connected"])
    ).count()
    
    # 3. Total Connections
    total_connections = db.query(DataSource).count()
    
    # 4. Sync Frequency (summary)
    sync_frequency = get_sync_frequency_summary(db)
    
    # 5. Validation Errors (open errors)
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
    """
    Calculate the sync frequency summary.
    Returns the most common frequency or '<5 min' for real-time.
    """
    sources = db.query(DataSource).all()
    
    if not sources:
        return "N/A"
    
    # Check for real-time sources
    realtime_count = db.query(DataSource).filter(
        DataSource.sync_frequency == "realtime"
    ).count()
    
    if realtime_count > 0:
        return "<5 min"
    
    # Check for hourly sources
    hourly_count = db.query(DataSource).filter(
        DataSource.sync_frequency == "hourly"
    ).count()
    
    if hourly_count > 0:
        return "~1 hour"
    
    # Get most common frequency
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
    """
    Sync data from a data source with full transaction support.
    """
    from sqlalchemy.exc import SQLAlchemyError
    
    ds = get_data_source(db, data_source_id)
    if not ds:
        return None
    
    # Create sync log - WITHOUT the new fields
    sync_log = SyncLog(
        datasource_id=ds.id,
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(sync_log)
    db.flush()
    
    ds.status = "syncing"
    ds.health = "unknown"
    db.flush()
    
    start_time = time.time()
    error_count = 0
    
    try:
        # BEGIN TRANSACTION
        # Fetch data
        data = fetch_data_from_source(ds)
        sync_log.rows_processed = len(data) if data else 0
        
        if not data:
            sync_log.status = "failed"
            sync_log.message = "No data retrieved"
            ds.status = "failed"
            ds.health = "unhealthy"
        else:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # STANDARDIZE FIRST
            source_type = get_source_type_name(ds.provider)
            df = ValidationEngine.standardize_dataframe(df, source_type)
            
            # VALIDATE SECOND
            is_valid, errors, stats = ValidationEngine.validate_dataframe(
                df, source_type, ds.name
            )
            
            # Store validation errors with details
            for error in errors:
                create_validation_error(
                    db,
                    source=f"datasource:{ds.id}",
                    error_type=error.get('column_name', 'unknown'),
                    severity=error.get('severity', 'medium'),
                    rows_affected=error.get('row_number', 0),
                    status="open",
                    column_name=error.get('column_name'),
                    row_number=error.get('row_number', 0),
                    expected_value=error.get('expected_value', ''),
                    actual_value=error.get('actual_value', ''),
                    error_message=error.get('error_message', ''),
                    suggestion=error.get('suggestion', '')
                )
            
            # Store data in transaction
            if is_valid or len(errors) < len(df) * 0.5:
                # Store raw data - all inserts happen in one transaction
                store_raw_data(db, df, ds.id, sync_log.id, source_type)
                
                # Calculate health based on last 10 syncs
                health_score = calculate_health_score(db, ds.id)
                ds.health = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy"
                ds.status = "success" if is_valid else "partial_success"
                sync_log.status = "success" if is_valid else "partial_success"
                sync_log.rows_validated = len(df) - len(errors)
            else:
                ds.status = "failed"
                ds.health = "unhealthy"
                sync_log.status = "failed"
                sync_log.message = f"Validation failed with {len(errors)} errors"
            
            sync_log.rows_failed = len(errors)
            ds.last_sync = datetime.utcnow()
        
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = time.time() - start_time
        
        # COMMIT TRANSACTION (all or nothing)
        db.commit()
        
    except SQLAlchemyError as e:
        # ROLLBACK on database error
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
        
    except Exception as e:
        # ROLLBACK on any error
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
    
    db.refresh(ds)
    return ds


def calculate_health_score(db: Session, datasource_id: int) -> float:
    """Calculate health score based on last 10 syncs."""
    recent_syncs = db.query(SyncLog).filter(
        SyncLog.datasource_id == datasource_id
    ).order_by(SyncLog.started_at.desc()).limit(10).all()
    
    if not recent_syncs:
        return 100.0
    
    # Calculate metrics
    total_syncs = len(recent_syncs)
    successful_syncs = sum(1 for s in recent_syncs if s.status == "success")
    total_duration = sum(s.duration_seconds or 0 for s in recent_syncs)
    avg_duration = total_duration / total_syncs if total_syncs > 0 else 0
    
    # Weighted scoring
    success_rate = (successful_syncs / total_syncs) * 100
    duration_score = max(0, 100 - (avg_duration / 10))  # 10 seconds = 100%, 60 seconds = 40%
    
    # Combined score
    health_score = (success_rate * 0.7) + (duration_score * 0.3)
    
    return min(100, health_score)


def fetch_data_from_source(ds: DataSource) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch data based on data source type.
    """
    try:
        if ds.type == DataSourceType.API:
            if not ds.base_url:
                raise ValueError("API data source requires base_url")
            
            headers = {}
            if ds.api_key:
                headers['Authorization'] = f'Bearer {ds.api_key}'
            
            # Add provider-specific headers
            if ds.provider == "SUPPLIER":
                headers['X-Supplier-API-Version'] = 'v2'
            
            return fetch_api(ds.base_url, headers=headers)
            
        elif ds.type == DataSourceType.DATABASE:
            if not ds.connection_string:
                raise ValueError("Database data source requires connection_string")
            
            # Use table_name from the data source
            table_name = ds.table_name
            if not table_name:
                # Try to infer from provider
                provider_table_map = {
                    "SAP": "sales",
                    "MYSQL": "sales",
                    "POSTGRES": "sales",
                    "SQLITE": "sales"
                }
                table_name = provider_table_map.get(str(ds.provider), "sales")
            
            if ds.provider == "MYSQL":
                return fetch_mysql_table(ds.connection_string, table_name)
            # elif ds.provider == "POSTGRES":
            #     return fetch_postgres_table(ds.connection_string, table_name)
            elif ds.provider == "SQLITE":
                return fetch_sqlite_table(ds.connection_string, table_name)
            else:
                raise ValueError(f"Unsupported database provider: {ds.provider}")
                
        elif ds.type == DataSourceType.LOCAL_FOLDER:
            if not ds.folder_path:
                raise ValueError("Folder data source requires folder_path")
            
            # If folder_path is a file path, read it
            if ds.folder_path.lower().endswith('.csv'):
                return fetch_csv(ds.folder_path)
            else:
                # Read all CSVs in folder
                from fastapi_app.services.connectors.folder_connector import fetch_all_csvs_in_folder
                result = fetch_all_csvs_in_folder(ds.folder_path)
                # Combine all data
                all_data = []
                for file_data in result.values():
                    all_data.extend(file_data)
                return all_data
                
        elif ds.type == DataSourceType.CLOUD_STORAGE:
            # TODO: Implement MinIO/S3 connector
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

def store_raw_data(db: Session, df: pd.DataFrame, datasource_id: int, 
                  sync_log_id: int, source_type: str) -> None:
    """
    Store validated data in appropriate raw tables.
    """
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
    
    for record in records:
        mapped_data = {}
        for source_field, target_field in mapping.items():
            if source_field in record:
                mapped_data[target_field] = record[source_field]
        
        mapped_data['datasource_id'] = datasource_id
        mapped_data['sync_id'] = sync_log_id
        
        # Convert record to JSON-serializable format
        # Fix: Convert Timestamp objects to strings
        raw_record = {}
        for key, value in record.items():
            if hasattr(value, 'to_pydatetime'):  # pandas Timestamp
                raw_record[key] = value.isoformat()
            elif hasattr(value, 'tolist'):  # numpy array
                raw_record[key] = value.tolist()
            elif hasattr(value, 'item'):  # numpy scalar
                raw_record[key] = value.item()
            else:
                raw_record[key] = value
        
        mapped_data['raw_data'] = raw_record  # Store cleaned record as JSON
        mapped_data['validation_status'] = "validated"
        
        try:
            obj = model_class(**mapped_data)
            db.add(obj)
        except Exception as e:
            logger.error(f"Error storing raw data: {str(e)}")
            continue
    
    db.commit()