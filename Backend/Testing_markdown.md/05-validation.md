# Demand Forecasting Backend API Reference — Validation

## 5. Validation

### 5.1 GET /api/validation/dashboard
Get validation dashboard statistics.

Success response:
```json
{
  "total_errors": 10,
  "open_errors": 4,
  "fixed_errors": 5,
  "ignored_errors": 1,
  "recent_errors": 3
}
```

### 5.2 GET /api/validation/errors
List validation errors.

Query parameters:
- `severity` (string)
- `status` (string)
- `source` (string)
- `start_date` (`date-time`)
- `end_date` (`date-time`)
- `page` (integer, default 1)
- `limit` (integer, default 20, max 100)

Success response:
```json
[
  {
    "id": 1,
    "source": "sales_data",
    "error_type": "missing_value",
    "severity": "high",
    "rows_affected": 50,
    "status": "open",
    "column_name": "quantity",
    "row_number": 42,
    "expected_value": "numeric",
    "actual_value": "",
    "error_message": "Missing quantity value",
    "suggestion": "Fill missing values or drop invalid rows",
    "fixed_reason": null,
    "ignored_reason": null,
    "fixed_by": null,
    "resolved_at": null,
    "created_at": "2026-07-24T10:47:44.399Z"
  }
]
```

### 5.3 GET /api/validation/errors/{error_id}
Get a validation error by ID.

Path parameter:
- `error_id` (integer)

Success response:
```json
{
  "id": 1,
  "source": "sales_data",
  "error_type": "missing_value",
  "severity": "high",
  "rows_affected": 50,
  "status": "open",
  "column_name": "quantity",
  "row_number": 42,
  "expected_value": "numeric",
  "actual_value": "",
  "error_message": "Missing quantity value",
  "suggestion": "Fill missing values or drop invalid rows",
  "fixed_reason": null,
  "ignored_reason": null,
  "fixed_by": null,
  "resolved_at": null,
  "created_at": "2026-07-24T10:47:44.406Z"
}
```

### 5.4 POST /api/validation/errors/{error_id}/fix
Fix a validation error.

Path parameter:
- `error_id` (integer)

Request body:
```json
{
  "fix_type": "fix",
  "comments": "Corrected missing quantity values.",
  "reason": "Auto-fill with zero"
}
```

Success response:
```json
{
  "id": 1,
  "source": "sales_data",
  "error_type": "missing_value",
  "severity": "high",
  "rows_affected": 50,
  "status": "fixed",
  "column_name": "quantity",
  "row_number": 42,
  "expected_value": "numeric",
  "actual_value": "",
  "error_message": "Missing quantity value",
  "suggestion": "Fill missing values or drop invalid rows",
  "fixed_reason": "Auto-fill with zero",
  "ignored_reason": null,
  "fixed_by": 1,
  "resolved_at": "2026-07-24T10:47:44.416Z",
  "created_at": "2026-07-24T10:47:44.416Z"
}
```

### 5.5 POST /api/validation/errors/{error_id}/ignore
Ignore a validation error.

Path parameter:
- `error_id` (integer)

Query parameter:
- `reason` (optional string)

Success response:
```json
{
  "id": 1,
  "source": "sales_data",
  "error_type": "missing_value",
  "severity": "high",
  "rows_affected": 50,
  "status": "ignored",
  "column_name": "quantity",
  "row_number": 42,
  "expected_value": "numeric",
  "actual_value": "",
  "error_message": "Missing quantity value",
  "suggestion": "Fill missing values or drop invalid rows",
  "fixed_reason": null,
  "ignored_reason": "Not relevant for this forecast",
  "fixed_by": 1,
  "resolved_at": "2026-07-24T10:47:44.425Z",
  "created_at": "2026-07-24T10:47:44.425Z"
}
```

### 5.6 POST /api/validation/errors/fix-all
Fix all open validation errors.

Request body:
```json
{
  "source": "sales_data",
  "reason": "Auto-fix all errors",
  "severity": "medium",
  "error_type": "missing_value"
}
```

Success response:
```json
{
  "fixed_count": 5,
  "message": "Fixed 5 validation errors"
}
```
