# Demand Forecasting Backend API Reference — Training

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Training Endpoints

### 1.1 GET /api/training/history
Get Training History

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_registry_id` | `query` | `any` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |

Success response:
```json
[
  {
    "id": 1,
    "version": "string",
    "accuracy_before": "any",
    "accuracy_after": "any",
    "improvement_percentage": "any",
    "rmse_before": "any",
    "rmse_after": "any",
    "mae_before": "any",
    "mae_after": "any",
    "mape_before": "any",
    "mape_after": "any",
    "duration_seconds": "any",
    "epochs": 20,
    "dataset_size": "any",
    "status": "string",
    "trained_at": "string",
    "started_at": "any",
    "finished_at": "any",
    "notes": "any",
    "metrics": "any"
  }
]
```

### 1.2 POST /api/training/jobs
Create Training Job

*Create a new training job.*

Request body:
```json
{
  "model_type": "transformer",
  "upload_id": "any",
  "csv_path": "any",
  "configuration": "any",
  "epochs": 20,
  "batch_size": 16,
  "learning_rate": 0.001
}
```

Success response:
```json
{
  "job_id": "string",
  "model_registry_id": "any",
  "upload_id": "any",
  "model_type": "transformer",
  "status": "string",
  "progress_percentage": 0.0,
  "current_epoch": 1,
  "total_epochs": "any",
  "current_step": "any",
  "current_step_name": "any",
  "current_step_message": "any",
  "failed_step": "any",
  "failed_step_name": "any",
  "started_at": "any",
  "completed_at": "any",
  "estimated_completion": "any",
  "elapsed_time": "any",
  "remaining_time": "any",
  "metrics": "any",
  "error_message": "any",
  "created_at": "string"
}
```

### 1.3 GET /api/training/jobs
List Training Jobs

*List training jobs.*

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
    "job_id": "string",
    "model_registry_id": "any",
    "upload_id": "any",
    "model_type": "transformer",
    "status": "string",
    "progress_percentage": 0.0,
    "current_epoch": 1,
    "total_epochs": "any",
    "current_step": "any",
    "current_step_name": "any",
    "current_step_message": "any",
    "failed_step": "any",
    "failed_step_name": "any",
    "started_at": "any",
    "completed_at": "any",
    "estimated_completion": "any",
    "elapsed_time": "any",
    "remaining_time": "any",
    "metrics": "any",
    "error_message": "any",
    "created_at": "string"
  }
]
```

### 1.4 GET /api/training/jobs/{job_id}
Get Training Job

*Get a specific training job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{
  "job_id": "string",
  "model_registry_id": "any",
  "upload_id": "any",
  "model_type": "transformer",
  "status": "string",
  "progress_percentage": 0.0,
  "current_epoch": 1,
  "total_epochs": "any",
  "current_step": "any",
  "current_step_name": "any",
  "current_step_message": "any",
  "failed_step": "any",
  "failed_step_name": "any",
  "started_at": "any",
  "completed_at": "any",
  "estimated_completion": "any",
  "elapsed_time": "any",
  "remaining_time": "any",
  "metrics": "any",
  "error_message": "any",
  "created_at": "string"
}
```

### 1.5 POST /api/training/jobs/{job_id}/cancel
Cancel Training Job

*Cancel a training job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```