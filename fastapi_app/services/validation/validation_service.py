# fastapi_app/services/validation/validation_service.py
import pandas as pd
from sqlalchemy.orm import Session
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import re
import logging

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
        
        # All validation rules - ALL use lowercase column names
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
        
        # Source-specific validation - ALL lowercase
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
        
        # Update statistics
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
        
        # ALL COLUMN NAMES ARE LOWERCASE
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
        
        # Expected types - ALL LOWERCASE
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
                    # Get sample of invalid values
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
                
                # Check for future dates
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
                
                # Check for very old dates
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
        # Convert to lowercase and replace spaces with underscores
        df.columns = [col.lower().strip().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Remove special characters from column names
        df.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in df.columns]
        
        # Standardize date columns
        for col in df.columns:
            if any(x in col for x in ['date', 'time', 'updated', 'created']):
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
        
        # Trim string columns
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
# HELPER FUNCTIONS - THESE WERE MISSING
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
    suggestion: str = None
) -> Any:
    """
    Create a validation error record.
    """
    from fastapi_app.models.validation_error_model import ValidationError
    from sqlalchemy.orm import Session
    
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
        suggestion=suggestion
    )
    db.add(err)
    db.commit()
    db.refresh(err)
    return err


def get_validation_errors(db: Session) -> List[Any]:
    """Get all validation errors"""
    from fastapi_app.models.validation_error_model import ValidationError
    
    return db.query(ValidationError).all()


def get_validation_error(db: Session, error_id: int) -> Optional[Any]:
    """Get a single validation error"""
    from fastapi_app.models.validation_error_model import ValidationError
    
    return db.query(ValidationError).filter(ValidationError.id == error_id).first()


def fix_validation_error(db: Session, error_id: int, fix_request: dict = None) -> Optional[Any]:
    """Mark a validation error as fixed"""
    from fastapi_app.models.validation_error_model import ValidationError
    
    err = get_validation_error(db, error_id)
    if not err:
        return None
    err.status = "fixed"
    db.commit()
    db.refresh(err)
    return err


def ignore_validation_error(db: Session, error_id: int) -> Optional[Any]:
    """Mark a validation error as ignored"""
    from fastapi_app.models.validation_error_model import ValidationError
    
    err = get_validation_error(db, error_id)
    if not err:
        return None
    err.status = "ignored"
    db.commit()
    db.refresh(err)
    return err


def fix_all_validation_errors(db: Session) -> int:
    """Mark all validation errors as fixed"""
    from fastapi_app.models.validation_error_model import ValidationError
    
    errors = db.query(ValidationError).all()
    for err in errors:
        err.status = "fixed"
    db.commit()
    return len(errors)