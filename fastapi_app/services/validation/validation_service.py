#fastapi_app/services/validation.validation_service.py

import pandas as pd
from sqlalchemy.orm import Session
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import re
import logging

from fastapi_app.models.validation_error_model import ValidationError
from fastapi_app.models.data_source_model import DataSource
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.sync_log_model import SyncLog

logger = logging.getLogger(__name__)

class ValidationEngine:
    """Enhanced validation engine for all data sources"""
    
    _pattern_cache = {}
    
    @staticmethod
    def validate_dataframe(
        df: pd.DataFrame, 
        source_type: str = None, 
        source_name: str = None,
        strict_mode: bool = False
    ) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validate a DataFrame and return validation results.
        IMPORTANT: DataFrame should ALREADY BE STANDARDIZED before calling this.
        """
        if df.empty:
            return False, [{
                "column_name": "data",
                "row_number": 0,
                "error_message": "Empty DataFrame",
                "severity": "critical",
                "expected_value": "non-empty data",
                "actual_value": "empty",
                "suggestion": "Check data source for content"
            }], {"total_rows": 0, "error_count": 1}
        
        errors = []
        stats = {
            "total_rows": len(df),
            "error_count": 0,
            "warning_count": 0,
            "columns": list(df.columns)
        }
        
        validation_rules = [
            ValidationEngine._validate_required_columns,
            ValidationEngine._validate_data_types,
            ValidationEngine._validate_numeric_ranges,
            ValidationEngine._validate_date_formats,
            ValidationEngine._validate_unique_constraints,
            ValidationEngine._validate_null_values,
        ]
        
        for rule_func in validation_rules:
            try:
                rule_errors = rule_func(df, source_type)
                if rule_errors:
                    errors.extend(rule_errors)
            except Exception as e:
                logger.error(f"Error in validation rule {rule_func.__name__}: {str(e)}")
                errors.append({
                    "column_name": "system",
                    "row_number": 0,
                    "error_message": f"Validation rule failed: {str(e)}",
                    "severity": "critical",
                    "expected_value": "valid data",
                    "actual_value": "error",
                    "suggestion": "Check validation configuration"
                })
        
        source_validators = {
            "sales": ValidationEngine._validate_sales_data,
            "inventory": ValidationEngine._validate_inventory_data,
            "supplier": ValidationEngine._validate_supplier_data,
            "products": ValidationEngine._validate_product_data,
        }
        
        if source_type and source_type in source_validators:
            try:
                source_errors = source_validators[source_type](df)
                if source_errors:
                    errors.extend(source_errors)
            except Exception as e:
                logger.error(f"Error in source validation for {source_type}: {str(e)}")
        
        for error in errors:
            if error.get('severity') in ['critical', 'high']:
                stats['error_count'] += 1
            else:
                stats['warning_count'] += 1
        
        is_valid = stats['error_count'] == 0
        
        return is_valid, errors, stats
    
    @staticmethod
    def _validate_required_columns(df: pd.DataFrame, source_type: str) -> List[Dict[str, Any]]:
        """Validate that required columns exist - ALL LOWERCASE"""
        errors = []
        
        required_columns_map = {
            "sales": ["date", "demand", "sku"],
            "inventory": ["sku", "stock", "warehouse"],
            "supplier": ["supplier", "sku", "price", "lead_time"],
            "products": ["sku", "name", "price"],
            "api": []
        }
        
        required_columns = required_columns_map.get(source_type, [])
        
        for col in required_columns:
            if col not in df.columns:
                errors.append({
                    "column_name": col,
                    "row_number": 0,
                    "error_message": f"Required column '{col}' is missing",
                    "severity": "high",
                    "expected_value": f"column '{col}' exists",
                    "actual_value": "missing",
                    "suggestion": f"Add column '{col}' to the data source or map it correctly"
                })
        
        return errors
    
    @staticmethod
    def _validate_data_types(df: pd.DataFrame, source_type: str) -> List[Dict[str, Any]]:
        """Validate data types - ALL LOWERCASE"""
        errors = []
        
        type_map = {
            'demand': 'numeric',
            'price': 'numeric',
            'revenue': 'numeric',
            'stock': 'numeric',
            'lead_time': 'numeric',
            'units': 'numeric',
            'date': 'datetime',
            'last_updated': 'datetime',
            'sku': 'string',
            'name': 'string',
            'category': 'string',
            'supplier': 'string',
            'warehouse': 'string',
        }
        
        for col in df.columns:
            col_lower = col.lower()
            
            if df[col].empty or df[col].isna().all():
                continue
            
            expected_type = type_map.get(col_lower)
            if not expected_type:
                continue
            
            if expected_type == 'numeric':
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                null_count = numeric_series.isna().sum()
                if null_count > 0:
                    invalid_values = df[col][numeric_series.isna()].head(5).tolist()
                    errors.append({
                        "column_name": col,
                        "row_number": 0,
                        "error_message": f"Column '{col}' contains {null_count} non-numeric values",
                        "severity": "medium",
                        "expected_value": "numeric value",
                        "actual_value": f"examples: {invalid_values}",
                        "suggestion": "Convert to numeric or check for invalid values"
                    })
            
            elif expected_type == 'datetime':
                try:
                    dates = pd.to_datetime(df[col], errors='coerce')
                    null_count = dates.isna().sum()
                    if null_count > 0:
                        invalid_values = df[col][dates.isna()].head(5).tolist()
                        errors.append({
                            "column_name": col,
                            "row_number": 0,
                            "error_message": f"Column '{col}' contains {null_count} invalid date formats",
                            "severity": "medium",
                            "expected_value": "ISO date format (YYYY-MM-DD)",
                            "actual_value": f"examples: {invalid_values}",
                            "suggestion": "Use ISO format (YYYY-MM-DD) or check for invalid dates"
                        })
                except:
                    errors.append({
                        "column_name": col,
                        "error_message": f"Column '{col}' has invalid date formats",
                        "severity": "high",
                        "expected_value": "valid date",
                        "actual_value": "invalid format",
                        "suggestion": "Use ISO format (YYYY-MM-DD) for dates"
                    })
        
        return errors
    
    @staticmethod
    def _validate_numeric_ranges(df: pd.DataFrame, source_type: str) -> List[Dict[str, Any]]:
        """Validate numeric ranges - ALL LOWERCASE"""
        errors = []
        
        range_checks = {
            "demand": (0, 1000000),
            "price": (0, 1000000),
            "revenue": (0, 10000000),
            "stock": (0, 10000000),
            "lead_time": (0, 365),
            "units": (0, 1000000),
        }
        
        for col, (min_val, max_val) in range_checks.items():
            if col in df.columns:
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                invalid_mask = (numeric_series < min_val) | (numeric_series > max_val)
                invalid_rows = df[invalid_mask]
                
                if not invalid_rows.empty:
                    errors.append({
                        "column_name": col,
                        "row_number": 0,
                        "error_message": f"Column '{col}' has {len(invalid_rows)} values outside range [{min_val}, {max_val}]",
                        "severity": "medium",
                        "expected_value": f"value between {min_val} and {max_val}",
                        "actual_value": f"examples: {invalid_rows[col].head(3).tolist()}",
                        "suggestion": f"Values should be between {min_val} and {max_val}"
                    })
        
        return errors
    
    @staticmethod
    def _validate_date_formats(df: pd.DataFrame, source_type: str) -> List[Dict[str, Any]]:
        """Validate date formats - ALL LOWERCASE"""
        errors = []
        
        date_columns = [col for col in df.columns if any(x in col.lower() for x in ['date', 'time', 'updated'])]
        
        for col in date_columns:
            try:
                dates = pd.to_datetime(df[col], errors='coerce')
                
                future_mask = dates > pd.Timestamp.now()
                if future_mask.any():
                    future_count = future_mask.sum()
                    future_examples = df[col][future_mask].head(3).tolist()
                    errors.append({
                        "column_name": col,
                        "row_number": 0,
                        "error_message": f"Column '{col}' contains {future_count} future dates",
                        "severity": "medium",
                        "expected_value": "date not in future",
                        "actual_value": f"examples: {future_examples}",
                        "suggestion": "Future dates may indicate incorrect data entry"
                    })
                
                min_date = pd.Timestamp('2000-01-01')
                old_mask = dates < min_date
                if old_mask.any():
                    old_count = old_mask.sum()
                    errors.append({
                        "column_name": col,
                        "row_number": 0,
                        "error_message": f"Column '{col}' contains {old_count} dates before 2000",
                        "severity": "low",
                        "expected_value": f"date after {min_date.date()}",
                        "actual_value": "very old date",
                        "suggestion": "Very old dates may indicate data quality issues"
                    })
                
            except Exception as e:
                errors.append({
                    "column_name": col,
                    "row_number": 0,
                    "error_message": f"Column '{col}' has invalid date formats",
                    "severity": "high",
                    "expected_value": "valid date format",
                    "actual_value": "invalid format",
                    "suggestion": "Use consistent date format like YYYY-MM-DD"
                })
        
        return errors
    
    @staticmethod
    def _validate_unique_constraints(df: pd.DataFrame, source_type: str) -> List[Dict[str, Any]]:
        """Validate unique constraints - ALL LOWERCASE"""
        errors = []
        
        unique_fields = {
            "sales": ["sku"],
            "inventory": ["sku", "warehouse"],
            "supplier": ["supplier", "sku"],
            "products": ["sku"],
        }
        
        fields_to_check = unique_fields.get(source_type, [])
        
        for field in fields_to_check:
            if field in df.columns and not df[field].isna().all():
                duplicates = df[field].duplicated()
                if duplicates.any():
                    duplicate_examples = df[field][duplicates].head(3).tolist()
                    errors.append({
                        "column_name": field,
                        "row_number": 0,
                        "error_message": f"Found {duplicates.sum()} duplicate {field} values",
                        "severity": "medium",
                        "expected_value": f"unique {field}",
                        "actual_value": f"examples: {duplicate_examples}",
                        "suggestion": f"Ensure each {field} is unique"
                    })
        
        return errors
    
    @staticmethod
    def _validate_null_values(df: pd.DataFrame, source_type: str) -> List[Dict[str, Any]]:
        """Validate null values - ALL LOWERCASE"""
        errors = []
        
        required_fields_map = {
            "sales": ["date", "demand"],
            "inventory": ["sku", "stock"],
            "supplier": ["sku", "price"],
            "products": ["sku", "name"],
        }
        
        required_fields = required_fields_map.get(source_type, [])
        
        for field in required_fields:
            if field in df.columns:
                null_count = df[field].isna().sum()
                if null_count > 0:
                    severity = "high" if null_count > len(df) * 0.5 else "medium"
                    errors.append({
                        "column_name": field,
                        "row_number": 0,
                        "error_message": f"Column '{field}' has {null_count} null values",
                        "severity": severity,
                        "expected_value": "non-null value",
                        "actual_value": "null",
                        "suggestion": f"Fill null values or investigate missing data"
                    })
        
        return errors
    
    # ============================================================================
    # SOURCE-SPECIFIC VALIDATION - ALL LOWERCASE
    # ============================================================================
    
    @staticmethod
    def _validate_sales_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Sales-specific validation - ALL LOWERCASE"""
        errors = []
        
        if 'demand' in df.columns:
            negative_demand = df[df['demand'] < 0]
            if not negative_demand.empty:
                errors.append({
                    "column_name": "demand",
                    "row_number": 0,
                    "error_message": f"Found {len(negative_demand)} records with negative demand",
                    "severity": "high",
                    "expected_value": "positive number",
                    "actual_value": f"examples: {negative_demand['demand'].head(3).tolist()}",
                    "suggestion": "Demand should be a positive number"
                })
        
        if 'date' in df.columns:
            try:
                dates = pd.to_datetime(df['date'])
                min_date = datetime(2020, 1, 1)
                max_date = datetime(2030, 12, 31)
                
                invalid_mask = (dates < min_date) | (dates > max_date)
                invalid_dates = df[invalid_mask]
                if not invalid_dates.empty:
                    errors.append({
                        "column_name": "date",
                        "row_number": 0,
                        "error_message": f"Found {len(invalid_dates)} dates outside range",
                        "severity": "medium",
                        "expected_value": f"date between {min_date.date()} and {max_date.date()}",
                        "actual_value": f"examples: {invalid_dates['date'].head(3).tolist()}",
                        "suggestion": f"Dates should be between {min_date.date()} and {max_date.date()}"
                    })
            except:
                pass
        
        return errors
    
    @staticmethod
    def _validate_inventory_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Inventory-specific validation - ALL LOWERCASE"""
        errors = []
        
        if 'stock' in df.columns:
            negative_stock = df[df['stock'] < 0]
            if not negative_stock.empty:
                errors.append({
                    "column_name": "stock",
                    "row_number": 0,
                    "error_message": f"Found {len(negative_stock)} records with negative stock",
                    "severity": "high",
                    "expected_value": "non-negative number",
                    "actual_value": f"examples: {negative_stock['stock'].head(3).tolist()}",
                    "suggestion": "Stock cannot be negative"
                })
        
        return errors
    
    @staticmethod
    def _validate_supplier_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Supplier-specific validation - ALL LOWERCASE"""
        errors = []
        
        if 'price' in df.columns:
            negative_price = df[df['price'] < 0]
            if not negative_price.empty:
                errors.append({
                    "column_name": "price",
                    "row_number": 0,
                    "error_message": f"Found {len(negative_price)} records with negative price",
                    "severity": "high",
                    "expected_value": "positive number",
                    "actual_value": f"examples: {negative_price['price'].head(3).tolist()}",
                    "suggestion": "Price must be positive"
                })
        
        if 'lead_time' in df.columns:
            invalid_lead_time = df[(df['lead_time'] < 0) | (df['lead_time'] > 365)]
            if not invalid_lead_time.empty:
                errors.append({
                    "column_name": "lead_time",
                    "row_number": 0,
                    "error_message": f"Found {len(invalid_lead_time)} records with invalid lead time",
                    "severity": "medium",
                    "expected_value": "between 0 and 365 days",
                    "actual_value": f"examples: {invalid_lead_time['lead_time'].head(3).tolist()}",
                    "suggestion": "Lead time should be between 0 and 365 days"
                })
        
        return errors
    
    @staticmethod
    def _validate_product_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Product-specific validation - ALL LOWERCASE"""
        errors = []
        
        if 'price' in df.columns:
            negative_price = df[df['price'] < 0]
            if not negative_price.empty:
                errors.append({
                    "column_name": "price",
                    "row_number": 0,
                    "error_message": f"Found {len(negative_price)} records with negative price",
                    "severity": "high",
                    "expected_value": "positive number",
                    "actual_value": f"examples: {negative_price['price'].head(3).tolist()}",
                    "suggestion": "Price must be positive"
                })
        
        if 'category' in df.columns:
            valid_categories = ['Electronics', 'Furniture', 'Clothing', 'Food', 'Toys', 'Books']
            invalid_categories = df[~df['category'].isin(valid_categories)]
            if not invalid_categories.empty:
                errors.append({
                    "column_name": "category",
                    "row_number": 0,
                    "error_message": f"Found {len(invalid_categories)} records with invalid categories",
                    "severity": "low",
                    "expected_value": f"one of: {valid_categories}",
                    "actual_value": f"examples: {invalid_categories['category'].head(3).tolist()}",
                    "suggestion": f"Valid categories: {', '.join(valid_categories)}"
                })
        
        return errors
    
    # ============================================================================
    # STANDARDIZATION - MUST BE CALLED BEFORE VALIDATION
    # ============================================================================
    
    @staticmethod
    def standardize_dataframe(df: pd.DataFrame, source_type: str = None) -> pd.DataFrame:
        """
        Standardize DataFrame columns for consistent storage.
        MUST BE CALLED BEFORE VALIDATION.
        """
        df.columns = [col.lower().strip().replace(' ', '_').replace('-', '_') for col in df.columns]
        df.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in df.columns]
        
        for col in df.columns:
            if any(x in col for x in ['date', 'time', 'updated', 'created']):
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
        
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]
        
        return df
    
    @staticmethod
    def get_validation_summary(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get a summary of validation errors."""
        summary = {
            "total_errors": len(errors),
            "by_severity": {},
            "by_column": {},
            "rows_affected": 0
        }
        
        for error in errors:
            severity = error.get('severity', 'unknown')
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            column = error.get('column_name', 'unknown')
            summary['by_column'][column] = summary['by_column'].get(column, 0) + 1
        
        return summary


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_validation_error(
    db: Session,
    source: str,
    error_type: str,
    severity: str = "medium",
    rows_affected: int = 0,
    status: str = "open",
    column_name: str = None,
    row_number: int = None,
    expected_value: str = None,
    actual_value: str = None,
    error_message: str = None,
    suggestion: str = None,
    datasource_id: int = None,
    upload_id: int = None,
    sync_id: int = None
) -> ValidationError:
    """
    Create a validation error record with proper foreign keys.
    """
    err = ValidationError(
        source=source,
        error_type=error_type,
        severity=severity,
        rows_affected=rows_affected,
        status=status,
        column_name=column_name,
        row_number=row_number,
        expected_value=expected_value,
        actual_value=actual_value,
        error_message=error_message,
        suggestion=suggestion,
        datasource_id=datasource_id,
        upload_id=upload_id,
        sync_id=sync_id
    )
    db.add(err)
    db.commit()
    db.refresh(err)
    return err


def get_validation_errors(
    db: Session,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0
) -> List[ValidationError]:
    """Get validation errors with filters."""
    query = db.query(ValidationError)
    
    if severity:
        query = query.filter(ValidationError.severity == severity)
    if status:
        query = query.filter(ValidationError.status == status)
    if source:
        query = query.filter(ValidationError.source == source)
    if start_date:
        query = query.filter(ValidationError.created_at >= start_date)
    if end_date:
        query = query.filter(ValidationError.created_at <= end_date)
    
    return query.order_by(ValidationError.created_at.desc()).offset(offset).limit(limit).all()


def get_validation_error(db: Session, error_id: int) -> Optional[ValidationError]:
    """Get a single validation error"""
    return db.query(ValidationError).filter(ValidationError.id == error_id).first()


def fix_validation_error(
    db: Session, 
    error_id: int, 
    fix_request: dict = None,
    resolved_by: int = None
) -> Optional[ValidationError]:
    """
    Mark a validation error as fixed with resolution tracking.
    """
    err = get_validation_error(db, error_id)
    if not err:
        return None
    
    err.status = "fixed"
    err.is_fixed = True
    err.resolved_at = datetime.utcnow()
    err.resolved_by = resolved_by
    
    if fix_request:
        if fix_request.get('comments'):
            err.fixed_reason = fix_request.get('comments')
        if fix_request.get('reason'):
            err.fixed_reason = fix_request.get('reason')
    
    db.commit()
    db.refresh(err)
    return err


def ignore_validation_error(
    db: Session, 
    error_id: int,
    resolved_by: int = None,
    reason: str = None
) -> Optional[ValidationError]:
    """
    Mark a validation error as ignored with resolution tracking.
    """
    err = get_validation_error(db, error_id)
    if not err:
        return None
    
    err.status = "ignored"
    err.is_ignored = True
    err.resolved_at = datetime.utcnow()
    err.resolved_by = resolved_by
    err.ignored_reason = reason
    
    db.commit()
    db.refresh(err)
    return err


def get_validation_statistics(db: Session) -> Dict[str, Any]:
    """
    Get statistics about validation errors.
    """
    from sqlalchemy import func
    
    total = db.query(func.count(ValidationError.id)).scalar() or 0
    open_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "open"
    ).scalar() or 0
    fixed_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "fixed"
    ).scalar() or 0
    ignored_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "ignored"
    ).scalar() or 0
    
    by_severity = {}
    for severity in ['critical', 'high', 'medium', 'low']:
        count = db.query(func.count(ValidationError.id)).filter(
            ValidationError.severity == severity
        ).scalar() or 0
        by_severity[severity] = count
    
    by_source = {}
    sources = db.query(ValidationError.source).distinct().all()
    for source in sources:
        source_name = source[0] if source[0] else "unknown"
        count = db.query(func.count(ValidationError.id)).filter(
            ValidationError.source == source_name
        ).scalar() or 0
        by_source[source_name] = count
    
    # Calculate resolution rate
    resolved = fixed_count + ignored_count
    resolution_rate = round((resolved / total) * 100 if total > 0 else 0, 1)
    
    return {
        "total": total,
        "open": open_count,
        "fixed": fixed_count,
        "ignored": ignored_count,
        "resolved": resolved,
        "resolution_rate": resolution_rate,
        "by_severity": by_severity,
        "by_source": by_source
    }


def create_validation_errors_batch(
    db: Session,
    errors: List[Dict[str, Any]],
    datasource_id: int = None,
    upload_id: int = None,
    sync_id: int = None,
    source_prefix: str = "datasource"
) -> int:
    """
    Create multiple validation errors in a single batch operation.
    """
    if not errors:
        return 0
    
    error_objects = []
    source_id = datasource_id if datasource_id else upload_id
    source_name = f"{source_prefix}:{source_id}" if source_id else "unknown"
    
    for error in errors:
        err = ValidationError(
            source=source_name,
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
            upload_id=upload_id,
            sync_id=sync_id
        )
        error_objects.append(err)
    
    if error_objects:
        db.bulk_save_objects(error_objects)
        db.commit()
        logger.debug(f"Stored {len(error_objects)} validation errors in batch")
    
    return len(error_objects)


def fix_all_validation_errors(
    db: Session,
    resolved_by: int = None,
    source: Optional[str] = None
) -> int:
    """
    Fix all open validation errors.
    """
    query = db.query(ValidationError).filter(
        ValidationError.status == "open"
    )
    if source:
        query = query.filter(ValidationError.source == source)
    
    now = datetime.utcnow()
    count = query.update({
        "status": "fixed",
        "is_fixed": True,
        "resolved_at": now,
        "resolved_by": resolved_by
    })
    db.commit()
    return count


def ignore_all_validation_errors(
    db: Session,
    resolved_by: int = None,
    source: Optional[str] = None,
    reason: str = None
) -> int:
    """
    Ignore all open validation errors.
    """
    query = db.query(ValidationError).filter(
        ValidationError.status == "open"
    )
    if source:
        query = query.filter(ValidationError.source == source)
    
    now = datetime.utcnow()
    count = query.update({
        "status": "ignored",
        "is_ignored": True,
        "resolved_at": now,
        "resolved_by": resolved_by,
        "ignored_reason": reason
    })
    db.commit()
    return count


def reopen_all_validation_errors(
    db: Session,
    source: Optional[str] = None
) -> int:
    """
    Reopen all fixed or ignored validation errors.
    """
    query = db.query(ValidationError).filter(
        ValidationError.status.in_(["fixed", "ignored"])
    )
    if source:
        query = query.filter(ValidationError.source == source)
    
    count = query.update({
        "status": "open",
        "is_fixed": False,
        "is_ignored": False,
        "resolved_at": None,
        "resolved_by": None
    })
    db.commit()
    return count