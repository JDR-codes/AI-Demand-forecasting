# Demand Forecasting Backend API Reference — Forecast Jobs

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Forecast Jobs Endpoints

### 1.1 POST /api/forecast/jobs/
Create Forecast Job

*Create a new forecast job.*

Request body:
```json
{
  "upload_id": "any",
  "model_registry_id": "any",
  "forecast_horizon": 7,
  "configuration": "any",
  "sku": "P0001",
  "region": "North",
  "warehouse": "S001"
}
```

Success response:
```json
{
  "id": 1,
  "job_id": "string",
  "upload_id": "any",
  "model_registry_id": "any",
  "status": "any",
  "progress_percentage": 0.0,
  "current_step": 1,
  "current_step_name": "any",
  "current_step_message": "any",
  "failed_step": "any",
  "failed_step_name": "any",
  "forecast_horizon": 7,
  "sku": "P0001",
  "region": "North",
  "warehouse": "S001",
  "started_at": "any",
  "completed_at": "any",
  "estimated_completion": "any",
  "elapsed_time": "any",
  "remaining_seconds": "any",
  "forecast_start_date": "any",
  "forecast_end_date": "any",
  "metrics": "any",
  "error_message": "any",
  "created_at": "string"
}
```

### 1.2 GET /api/forecast/jobs/
List Forecast Jobs

*List forecast jobs with optional filtering.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `status` | `query` | `any` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |
| `offset` | `query` | `integer` | No | - | - |

Success response:
```json
[
  {
    "id": 1,
    "job_id": "string",
    "upload_id": "any",
    "model_registry_id": "any",
    "status": "any",
    "progress_percentage": 0.0,
    "current_step": 1,
    "current_step_name": "any",
    "current_step_message": "any",
    "failed_step": "any",
    "failed_step_name": "any",
    "forecast_horizon": 7,
    "sku": "P0001",
    "region": "North",
    "warehouse": "S001",
    "started_at": "any",
    "completed_at": "any",
    "estimated_completion": "any",
    "elapsed_time": "any",
    "remaining_seconds": "any",
    "forecast_start_date": "any",
    "forecast_end_date": "any",
    "metrics": "any",
    "error_message": "any",
    "created_at": "string"
  }
]
```

### 1.3 GET /api/forecast/jobs/{job_id}
Get Forecast Job

*Get a specific forecast job with steps and results.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{
  "id": 1,
  "job_id": "string",
  "upload_id": "any",
  "model_registry_id": "any",
  "status": "any",
  "progress_percentage": 0.0,
  "current_step": 1,
  "current_step_name": "any",
  "current_step_message": "any",
  "failed_step": "any",
  "failed_step_name": "any",
  "forecast_horizon": 7,
  "sku": "P0001",
  "region": "North",
  "warehouse": "S001",
  "started_at": "any",
  "completed_at": "any",
  "estimated_completion": "any",
  "elapsed_time": "any",
  "remaining_seconds": "any",
  "forecast_start_date": "any",
  "forecast_end_date": "any",
  "metrics": "any",
  "error_message": "any",
  "created_at": "string"
}
```

### 1.4 DELETE /api/forecast/jobs/{job_id}
Delete Forecast Job

*Delete a forecast job (only if not running).*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.5 POST /api/forecast/jobs/{job_id}/cancel
Cancel Forecast Job

*Cancel a forecast job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.6 GET /api/forecast/jobs/{job_id}/chart
Get Forecast Chart

*Get chart data for the forecast.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.7 POST /api/forecast/jobs/{job_id}/pause
Pause Forecast Job

*Pause a running forecast job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.8 GET /api/forecast/jobs/{job_id}/peaks
Get Forecast Peaks

*Get peak demand days.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |
| `top_n` | `query` | `integer` | No | - | - |

Success response:
```json
{}
```

### 1.9 GET /api/forecast/jobs/{job_id}/results
Get Forecast Results

*Get forecast results with historical/forecast separation.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{
  "historical": [],
  "forecast": [],
  "upper": [],
  "lower": [],
  "labels": [],
  "split_index": 1,
  "total_points": 1,
  "peak_days": [],
  "forecast_start": "any"
}
```

### 1.10 POST /api/forecast/jobs/{job_id}/resume
Resume Forecast Job

*Resume a paused forecast job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.11 POST /api/forecast/jobs/{job_id}/retry
Retry Forecast Job

*Retry a failed forecast job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.12 POST /api/forecast/jobs/{job_id}/start
Start Forecast Job

*Start a forecast job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{
  "id": 1,
  "job_id": "string",
  "upload_id": "any",
  "model_registry_id": "any",
  "status": "any",
  "progress_percentage": 0.0,
  "current_step": 1,
  "current_step_name": "any",
  "current_step_message": "any",
  "failed_step": "any",
  "failed_step_name": "any",
  "forecast_horizon": 7,
  "sku": "P0001",
  "region": "North",
  "warehouse": "S001",
  "started_at": "any",
  "completed_at": "any",
  "estimated_completion": "any",
  "elapsed_time": "any",
  "remaining_seconds": "any",
  "forecast_start_date": "any",
  "forecast_end_date": "any",
  "metrics": "any",
  "error_message": "any",
  "created_at": "string"
}
```

### 1.13 GET /api/forecast/jobs/{job_id}/status
Get Forecast Live Status

*Get live status for UI.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.14 GET /api/forecast/jobs/{job_id}/steps
Get Forecast Job Steps

*Get steps for a forecast job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
[
  {
    "id": 1,
    "step_number": 1,
    "step_name": "string",
    "status": "string",
    "progress": 0.0,
    "started_at": "any",
    "completed_at": "any",
    "duration_seconds": "any",
    "message": "any"
  }
]
```

### 1.15 GET /api/forecast/jobs/{job_id}/summary
Get Forecast Summary

*Get summary statistics.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{
  "forecasted_demand": 0.0,
  "avg_daily_demand": 0.0,
  "peak_day": 1,
  "peak_value": 0.0,
  "expected_revenue": 0.0,
  "inventory_risk": "string",
  "accuracy": 0.0,
  "total_points": 1,
  "confidence_level": 0.0,
  "unit_price_used": 0.0
}
```