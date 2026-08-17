# fastapi_app/services/validation/validation_service.py
import pandas as pd
from sqlalchemy.orm import Session
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import re
import logging

from fastapi_app.models.validation_error_model import ValidationError

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
                "error_type": "Empty Data",
                "column_name": "data",
                "row_number": 0,
                "rows_affected": 0,
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
                    "error_type": "System Error",
                    "column_name": "system",
                    "row_number": 0,
                    "rows_affected": 1,
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

        # Categorize errors by severity
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
                    "error_type": "Missing Column",
                    "column_name": col,
                    "row_number": 0,
                    "rows_affected": len(df),
                    "error_message": f"Required column '{col}' is missing",
                    "severity": "high",
                    "expected_value": f"column '{col}' exists",
                    "actual_value": "missing",
                    "suggestion": f"Add column '{col}' to the data source or map it correctly"
                })

        return errors

    @staticmethod
    def _validate_data_types(
        df: pd.DataFrame,
        source_type: str
    ) -> List[Dict[str, Any]]:
        """Validate data types without treating actual nulls as invalid values."""

        errors = []

        type_map = {
            "demand": "numeric",
            "price": "numeric",
            "revenue": "numeric",
            "stock": "numeric",
            "lead_time": "numeric",
            "units": "numeric",
            "reorder_level": "numeric",
            "min_order": "numeric",

            "date": "datetime",
            "last_updated": "datetime",

            "sku": "string",
            "name": "string",
            "category": "string",
            "supplier": "string",
            "warehouse": "string",
        }

        for col in df.columns:

            if df[col].empty or df[col].isna().all():
                continue

            expected_type = type_map.get(col.lower())

            if not expected_type:
                continue

            # ---------------------------------------------------------
            # NUMERIC
            # ---------------------------------------------------------

            if expected_type == "numeric":

                numeric_series = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

                # Invalid only when original value exists but
                # conversion produced NaN
                invalid_mask = (
                    numeric_series.isna()
                    & df[col].notna()
                )

                invalid_count = int(invalid_mask.sum())

                if invalid_count > 0:

                    invalid_values = (
                        df.loc[invalid_mask, col]
                        .head(5)
                        .tolist()
                    )

                    errors.append({
                        "error_type": "Invalid Numeric Values",
                        "column_name": col,
                        "row_number": 0,
                        "rows_affected": invalid_count,
                        "error_message": (
                            f"Column '{col}' contains "
                            f"{invalid_count} non-numeric values"
                        ),
                        "severity": "medium",
                        "expected_value": "numeric value",
                        "actual_value": (
                            f"examples: {invalid_values}"
                        ),
                        "suggestion": (
                            "Convert invalid values to numeric "
                            "or correct the source data"
                        )
                    })

            # ---------------------------------------------------------
            # DATETIME
            # ---------------------------------------------------------

            elif expected_type == "datetime":

                dates = pd.to_datetime(
                    df[col],
                    errors="coerce"
                )

                invalid_mask = (
                    dates.isna()
                    & df[col].notna()
                )

                invalid_count = int(invalid_mask.sum())

                if invalid_count > 0:

                    invalid_values = (
                        df.loc[invalid_mask, col]
                        .head(5)
                        .tolist()
                    )

                    errors.append({
                        "error_type": "Invalid Dates",
                        "column_name": col,
                        "row_number": 0,
                        "rows_affected": invalid_count,
                        "error_message": (
                            f"Column '{col}' contains "
                            f"{invalid_count} invalid date values"
                        ),
                        "severity": "medium",
                        "expected_value": (
                            "valid date such as YYYY-MM-DD"
                        ),
                        "actual_value": (
                            f"examples: {invalid_values}"
                        ),
                        "suggestion": (
                            "Use a valid and consistent date format"
                        )
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
                invalid_count = len(invalid_rows)

                if invalid_count > 0:
                    errors.append({
                        "error_type": "Out of Range",
                        "column_name": col,
                        "row_number": 0,
                        "rows_affected": invalid_count,
                        "error_message": f"Column '{col}' has {invalid_count} values outside range [{min_val}, {max_val}]",
                        "severity": "medium",
                        "expected_value": f"value between {min_val} and {max_val}",
                        "actual_value": f"examples: {invalid_rows[col].head(3).tolist()}",
                        "suggestion": f"Values should be between {min_val} and {max_val}"
                    })

        return errors

    @staticmethod
    def _validate_date_formats(
        df: pd.DataFrame,
        source_type: str
    ) -> List[Dict[str, Any]]:

        errors = []

        date_columns = [
            col
            for col in df.columns
            if any(
                x in col.lower()
                for x in ["date", "time", "updated"]
            ) and not any(
                y in col.lower()
                for y in ["lead_time", "leadtime"]
            )
        ]

        for col in date_columns:

            dates = pd.to_datetime(
                df[col],
                errors="coerce"
            )

            # Sales date range is handled by _validate_sales_data()
            if not (source_type == "sales" and col == "date"):

                future_mask = (
                    dates.notna()
                    & (dates > pd.Timestamp.now())
                )

                if future_mask.any():

                    future_count = int(future_mask.sum())

                    future_examples = (
                        df.loc[future_mask, col]
                        .head(3)
                        .tolist()
                    )

                    errors.append({
                        "error_type": "Future Dates",
                        "column_name": col,
                        "row_number": 0,
                        "rows_affected": future_count,
                        "error_message": (
                            f"Column '{col}' contains "
                            f"{future_count} future dates"
                        ),
                        "severity": "medium",
                        "expected_value": "date not in future",
                        "actual_value": (
                            f"examples: {future_examples}"
                        ),
                        "suggestion": (
                            "Future dates may indicate "
                            "incorrect data entry"
                        )
                    })

            min_date = pd.Timestamp("2000-01-01")

            old_mask = (
                dates.notna()
                & (dates < min_date)
            )

            if old_mask.any():

                old_count = int(old_mask.sum())

                errors.append({
                    "error_type": "Very Old Dates",
                    "column_name": col,
                    "row_number": 0,
                    "rows_affected": old_count,
                    "error_message": (
                        f"Column '{col}' contains "
                        f"{old_count} dates before 2000"
                    ),
                    "severity": "low",
                    "expected_value": (
                        f"date after {min_date.date()}"
                    ),
                    "actual_value": "very old date",
                    "suggestion": (
                        "Very old dates may indicate "
                        "data quality issues"
                    )
                })

        return errors

    @staticmethod
    def _validate_unique_constraints(
        df: pd.DataFrame,
        source_type: str
    ) -> List[Dict[str, Any]]:
        """Validate composite unique constraints."""
        errors = []

        # Dynamic composite unique constraints based on columns present
        sales_fields = ["date", "sku"]
        if "store_id" in df.columns:
            sales_fields.append("store_id")
        elif "store" in df.columns:
            sales_fields.append("store")
        elif "region" in df.columns:
            sales_fields.append("region")

        unique_constraints = {
            "sales": [sales_fields],
            "inventory": [["sku", "warehouse"]],
            "supplier": [["supplier", "sku"]],
            "products": [["sku"]],
        }

        constraints = unique_constraints.get(source_type, [])

        for fields in constraints:
            if not all(field in df.columns for field in fields):
                continue

            duplicate_mask = df.duplicated(subset=fields, keep="first")
            duplicate_count = int(duplicate_mask.sum())

            if duplicate_count > 0:
                examples = (
                    df.loc[duplicate_mask, fields]
                    .head(3)
                    .astype(str)
                    .to_dict("records")
                )

                errors.append({
                    "error_type": "Duplicate Rows",
                    "column_name": ", ".join(fields),
                    "row_number": 0,
                    "rows_affected": duplicate_count,
                    "error_message": (
                        f"Found {duplicate_count} duplicate "
                        f"records for {', '.join(fields)}"
                    ),
                    "severity": "medium",
                    "expected_value": f"unique combination of {', '.join(fields)}",
                    "actual_value": f"examples: {examples}",
                    "suggestion": "Remove or merge duplicate records",
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
                        "error_type": "Missing Values",
                        "column_name": field,
                        "row_number": 0,
                        "rows_affected": int(null_count),
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
    def _validate_sales_data(
        df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Sales-specific validation."""

        errors = []

        # ============================================================
        # DEMAND
        # ============================================================

        if "demand" in df.columns:

            demand_series = pd.to_numeric(
                df["demand"],
                errors="coerce"
            )

            negative_mask = demand_series < 0
            negative_count = int(negative_mask.sum())

            if negative_count > 0:

                errors.append({
                    "error_type": "Negative Demand",
                    "column_name": "demand",
                    "row_number": 0,
                    "rows_affected": negative_count,
                    "error_message": (
                        f"Found {negative_count} records "
                        "with negative demand"
                    ),
                    "severity": "high",
                    "expected_value": "non-negative number",
                    "actual_value": (
                        f"examples: "
                        f"{df.loc[negative_mask, 'demand'].head(3).tolist()}"
                    ),
                    "suggestion": (
                        "Demand must be zero or greater"
                    )
                })

        # ============================================================
        # DATE RANGE
        # ============================================================

        if "date" in df.columns:

            dates = pd.to_datetime(
                df["date"],
                errors="coerce"
            )

            min_date = pd.Timestamp("2020-01-01")
            max_date = pd.Timestamp.now().normalize()

            range_mask = (
                dates.notna()
                & (
                    (dates < min_date)
                    | (dates > max_date)
                )
            )

            range_count = int(range_mask.sum())

            if range_count > 0:

                examples = (
                    df.loc[range_mask, "date"]
                    .head(3)
                    .tolist()
                )

                errors.append({
                    "error_type": "Out of Range",
                    "column_name": "date",
                    "row_number": 0,
                    "rows_affected": range_count,
                    "error_message": (
                        f"Found {range_count} sales dates "
                        "outside the allowed range"
                    ),
                    "severity": "medium",
                    "expected_value": (
                        f"date between {min_date.date()} "
                        f"and {max_date.date()}"
                    ),
                    "actual_value": (
                        f"examples: {examples}"
                    ),
                    "suggestion": (
                        "Sales dates must not be before "
                        "2020-01-01 or in the future"
                    )
                })

        return errors


    @staticmethod
    def _validate_inventory_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Inventory-specific validation - ALL LOWERCASE"""
        errors = []

        if "stock" in df.columns:
            stock_series = pd.to_numeric(df["stock"], errors="coerce")
            negative_mask = stock_series < 0
            negative_stock = df[negative_mask]
            negative_count = int(negative_mask.sum())

            if negative_count > 0:
                errors.append({
                    "error_type": "Negative Stock",
                    "column_name": "stock",
                    "row_number": 0,
                    "rows_affected": negative_count,
                    "error_message": (
                        f"Found {negative_count} records "
                        "with negative stock"
                    ),
                    "severity": "high",
                    "expected_value": "non-negative number",
                    "actual_value": (
                        f"examples: "
                        f"{negative_stock['stock'].head(3).tolist()}"
                    ),
                    "suggestion": "Stock cannot be negative"
                })

        return errors


    @staticmethod
    def _validate_supplier_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Supplier-specific validation - ALL LOWERCASE"""
        errors = []

        if "price" in df.columns:
            price_series = pd.to_numeric(df["price"], errors="coerce")
            negative_mask = price_series < 0
            negative_price = df[negative_mask]
            negative_count = int(negative_mask.sum())

            if negative_count > 0:
                errors.append({
                    "error_type": "Negative Price",
                    "column_name": "price",
                    "row_number": 0,
                    "rows_affected": negative_count,
                    "error_message": (
                        f"Found {negative_count} records "
                        "with negative price"
                    ),
                    "severity": "high",
                    "expected_value": "non-negative number",
                    "actual_value": (
                        f"examples: "
                        f"{negative_price['price'].head(3).tolist()}"
                    ),
                    "suggestion": "Price must be zero or greater"
                })

        if "lead_time" in df.columns:
            lead_time_series = pd.to_numeric(df["lead_time"], errors="coerce")
            invalid_mask = (lead_time_series < 0) | (lead_time_series > 365)
            invalid_lead_time = df[invalid_mask]
            invalid_count = int(invalid_mask.sum())

            if invalid_count > 0:
                errors.append({
                    "error_type": "Out of Range",
                    "column_name": "lead_time",
                    "row_number": 0,
                    "rows_affected": invalid_count,
                    "error_message": (
                        f"Found {invalid_count} records "
                        "with invalid lead time"
                    ),
                    "severity": "medium",
                    "expected_value": "between 0 and 365 days",
                    "actual_value": (
                        f"examples: "
                        f"{invalid_lead_time['lead_time'].head(3).tolist()}"
                    ),
                    "suggestion": "Lead time should be between 0 and 365 days"
                })

        return errors


    @staticmethod
    def _validate_product_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Product-specific validation - ALL LOWERCASE"""
        errors = []

        if "price" in df.columns:
            price_series = pd.to_numeric(df["price"], errors="coerce")
            negative_mask = price_series < 0
            negative_price = df[negative_mask]
            negative_count = int(negative_mask.sum())

            if negative_count > 0:
                errors.append({
                    "error_type": "Negative Price",
                    "column_name": "price",
                    "row_number": 0,
                    "rows_affected": negative_count,
                    "error_message": (
                        f"Found {negative_count} records "
                        "with negative price"
                    ),
                    "severity": "high",
                    "expected_value": "non-negative number",
                    "actual_value": (
                        f"examples: "
                        f"{negative_price['price'].head(3).tolist()}"
                    ),
                    "suggestion": "Price must be zero or greater"
                })

        if 'category' in df.columns:
            valid_categories = ['Electronics', 'Furniture', 'Clothing', 'Food', 'Toys', 'Books', 'Home & Kitchen', 'Sports', 'Beauty', 'Groceries']
            invalid_categories = df[~df['category'].isin(valid_categories)]
            invalid_count = len(invalid_categories)
            if invalid_count > 0:
                errors.append({
                    "error_type": "Invalid Category",
                    "column_name": "category",
                    "row_number": 0,
                    "rows_affected": invalid_count,
                    "error_message": f"Found {invalid_count} records with invalid categories",
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
    def standardize_dataframe(
        df: pd.DataFrame,
        source_type: str = None
    ) -> pd.DataFrame:
        """
        Standardize column names and string values.

        IMPORTANT:
        Do not convert dates or numeric values here.
        Validation must see the original invalid values.
        """

        df = df.copy()

        # Standardize column names
        df.columns = [
            str(col)
            .lower()
            .strip()
            .replace(" ", "_")
            .replace("-", "_")
            for col in df.columns
        ]

        df.columns = [
            re.sub(r"[^a-zA-Z0-9_]", "", col)
            for col in df.columns
        ]

        # Map common aliases to expected columns
        aliases = {
            "product_id": "sku",
            "productid": "sku",
            "item_id": "sku",
            "item_no": "sku",
            
            "units_sold": "demand",
            "quantity_sold": "demand",
            "sales": "demand",
            "sales_volume": "demand",
            
            "stock_level": "stock",
            "inventory_level": "stock",
            "quantity_on_hand": "stock",
            "on_hand": "stock",
            
            "leadtime": "lead_time",
        }
        
        # Rename columns that match aliases but ONLY if the target column does not already exist
        rename_dict = {}
        for col in df.columns:
            if col in aliases:
                target_col = aliases[col]
                if target_col not in df.columns:
                    rename_dict[col] = target_col
                    
        if rename_dict:
            df = df.rename(columns=rename_dict)

        # Strip whitespace from string columns
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].apply(
                lambda value: value.strip()
                if isinstance(value, str)
                else value
            )

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

            rows = int(error.get('rows_affected', 0))
            summary['rows_affected'] += rows

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
    """Get ACTIVE validation errors only."""
    query = db.query(ValidationError).filter(
        ValidationError.status == "open",
        ValidationError.is_fixed.is_(False),
        ValidationError.is_ignored.is_(False)
    )

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
    resolved_by: int = None,
    comments: str = None
) -> Optional[ValidationError]:
    """
    Mark a validation error as fixed with resolution tracking.
    """
    err = get_validation_error(db, error_id)
    if not err:
        return None

    now = datetime.utcnow()

    err.status = "fixed"
    err.is_fixed = True
    err.fixed_reason = comments
    err.fixed_by = resolved_by
    err.fixed_time = now
    err.resolved_at = now
    err.resolved_by = resolved_by
    err.resolution_notes = comments

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

    now = datetime.utcnow()

    err.status = "ignored"
    err.is_ignored = True
    err.ignored_reason = reason
    err.resolved_at = now
    err.resolved_by = resolved_by
    err.resolution_notes = reason

    db.commit()
    db.refresh(err)
    return err


def get_validation_statistics(db: Session) -> Dict[str, Any]:
    """
    Get statistics about validation errors (active only).
    """
    from sqlalchemy import func

    total = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "open",
        ValidationError.is_fixed.is_(False),
        ValidationError.is_ignored.is_(False)
    ).scalar() or 0

    # Historical counts for dashboard
    fixed_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "fixed"
    ).scalar() or 0

    ignored_count = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "ignored"
    ).scalar() or 0

    by_severity = {}
    for severity in ['critical', 'high', 'medium', 'low']:
        count = db.query(func.count(ValidationError.id)).filter(
            ValidationError.severity == severity,
            ValidationError.status == "open",
            ValidationError.is_fixed.is_(False),
            ValidationError.is_ignored.is_(False)
        ).scalar() or 0
        by_severity[severity] = count

    by_source = {}
    sources = db.query(ValidationError.source).distinct().filter(
        ValidationError.status == "open",
        ValidationError.is_fixed.is_(False),
        ValidationError.is_ignored.is_(False)
    ).all()
    for source in sources:
        source_name = source[0] if source[0] else "unknown"
        count = db.query(func.count(ValidationError.id)).filter(
            ValidationError.source == source_name,
            ValidationError.status == "open",
            ValidationError.is_fixed.is_(False),
            ValidationError.is_ignored.is_(False)
        ).scalar() or 0
        by_source[source_name] = count

    # Calculate resolution rate
    resolved = fixed_count + ignored_count
    all_errors = fixed_count + ignored_count + total
    resolution_rate = round((resolved / all_errors) * 100 if all_errors > 0 else 0, 1)

    return {
        "total": total,
        "open": total,
        "fixed": fixed_count,
        "ignored": ignored_count,
        "resolved": resolved,
        "resolution_rate": resolution_rate,
        "by_severity": by_severity,
        "by_source": by_source
    }


def fix_all_validation_errors(
    db: Session,
    resolved_by: int = None,
    source: Optional[str] = None,
    comments: str = None
) -> int:
    """
    Fix all open validation errors (manual fix-all).
    """
    query = db.query(ValidationError).filter(
        ValidationError.status == "open",
        ValidationError.is_fixed.is_(False),
        ValidationError.is_ignored.is_(False)
    )
    if source:
        query = query.filter(ValidationError.source == source)

    now = datetime.utcnow()
    count = query.update({
        "status": "fixed",
        "is_fixed": True,
        "fixed_reason": comments,
        "fixed_by": resolved_by,
        "fixed_time": now,
        "resolved_at": now,
        "resolved_by": resolved_by,
        "resolution_notes": comments
    })
    db.commit()
    return count


def auto_fix_all_validation_errors(
    db: Session,
    resolved_by: int = None
) -> Dict[str, Any]:
    """
    Auto-fix all fixable validation errors.

    Only fixes errors that have deterministic corrections:
    - Missing Values (can fill with defaults)
    - Duplicate Rows (can keep first)
    - Invalid Numeric Values (can coerce)
    """
    from sqlalchemy import func

    now = datetime.utcnow()

    # Count total active errors
    total = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "open",
        ValidationError.is_fixed.is_(False),
        ValidationError.is_ignored.is_(False)
    ).scalar() or 0

    # Auto-fixable error types
    fixable_types = ["Missing Values", "Duplicate Rows", "Invalid Numeric Values"]

    # Fix auto-fixable errors
    query = db.query(ValidationError).filter(
        ValidationError.status == "open",
        ValidationError.is_fixed.is_(False),
        ValidationError.is_ignored.is_(False),
        ValidationError.error_type.in_(fixable_types)
    )

    fixed = query.update({
        "status": "fixed",
        "is_fixed": True,
        "fixed_reason": "Auto-fixed by system",
        "fixed_by": resolved_by,
        "fixed_time": now,
        "resolved_at": now,
        "resolved_by": resolved_by,
        "resolution_notes": "Auto-fixed by system"
    })

    db.commit()

    # Count remaining
    remaining = db.query(func.count(ValidationError.id)).filter(
        ValidationError.status == "open",
        ValidationError.is_fixed.is_(False),
        ValidationError.is_ignored.is_(False)
    ).scalar() or 0

    return {
        "total": total,
        "fixed": fixed,
        "remaining": remaining,
        "message": f"Auto-fixed {fixed} errors, {remaining} remaining"
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
    Create multiple validation errors in a single batch operation with aggregation.
    Uses rows_affected from each error for accurate counts.
    """
    if not errors:
        return 0

    # Group errors by type/column for aggregated rows_affected
    error_groups = {}
    source_id = datasource_id if datasource_id else upload_id
    source_name = f"{source_prefix}:{source_id}" if source_id else "unknown"

    for error in errors:
        key = f"{error.get('error_type', 'unknown')}:{error.get('column_name', 'unknown')}"
        if key not in error_groups:
            error_groups[key] = {
                "error_type": error.get('error_type', 'unknown'),
                "column_name": error.get('column_name'),
                "severity": error.get('severity', 'medium'),
                "expected_value": error.get('expected_value', ''),
                "actual_value": error.get('actual_value', ''),
                "error_message": error.get('error_message', ''),
                "suggestion": error.get('suggestion', ''),
                "row_count": int(error.get('rows_affected', 0))
            }
        else:
            error_groups[key]["row_count"] += int(error.get('rows_affected', 0))

    error_objects = []
    for key, group in error_groups.items():
        err = ValidationError(
            source=source_name,
            error_type=group["error_type"],
            severity=group["severity"],
            rows_affected=group["row_count"],
            status="open",
            column_name=group["column_name"],
            row_number=0,
            expected_value=group["expected_value"],
            actual_value=group["actual_value"],
            error_message=f"{group['error_message']} (affected {group['row_count']} rows)",
            suggestion=group["suggestion"],
            datasource_id=datasource_id,
            upload_id=upload_id,
            sync_id=sync_id
        )
        error_objects.append(err)

    if error_objects:
        db.bulk_save_objects(error_objects)
        db.commit()
        logger.debug(f"Stored {len(error_objects)} aggregated validation errors")

    return len(error_objects)