# Demand Forecasting Backend API Reference — Forecast

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Forecast Endpoints

### 1.1 GET /api/forecast/dashboard
Forecast Dashboard

*Get forecast dashboard summary with metrics.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_type` | `query` | `any` | No | Filter by model type | `"transformer"` |

Success response:
```json
{
  "total_jobs": 1,
  "completed_jobs": 1,
  "failed_jobs": 1,
  "running_jobs": 1,
  "queued_jobs": 1,
  "total_forecasts": 1,
  "active_models": 1,
  "total_models": 1,
  "average_accuracy": "any",
  "average_rmse": "any",
  "average_mae": "any",
  "average_mape": "any",
  "latest_training": "any",
  "best_model": "any",
  "recent_jobs": "any",
  "training_jobs": "any",
  "timestamp": "any"
}
```

### 1.2 GET /api/forecast/metrics/best
Get Best Model

*Get the best performing model.*

Success response:
```json
{
  "anyOf": [
    {
      "additionalProperties": true,
      "type": "object"
    },
    {
      "type": "null"
    }
  ],
  "title": "Response Get Best Model Api Forecast Metrics Best Get"
}
```

### 1.3 GET /api/forecast/metrics/comparison
Get Metrics Comparison

*Get comparison metrics across model types.*

Success response:
```json
{
  "items": {
    "additionalProperties": true,
    "type": "object"
  },
  "type": "array",
  "title": "Response Get Metrics Comparison Api Forecast Metrics Comparison Get"
}
```

### 1.4 GET /api/forecast/metrics/history
Get Metrics History

*Get historical metrics for chart.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `days` | `query` | `integer` | No | - | - |
| `model_type` | `query` | `any` | No | Filter by model type | `"transformer"` |

Success response:
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "additionalProperties": true
  },
  "title": "Response Get Metrics History Api Forecast Metrics History Get"
}
```

### 1.5 GET /api/forecast/models/{model_id}/config
Get Model Config

*Get model configuration for the Figma popup.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{
  "id": "string",
  "name": "string",
  "model_type": "transformer",
  "forecast_horizon": 7,
  "seasonality": true,
  "validation_split": 0.0,
  "default_dataset": "any",
  "default_region": "any",
  "default_sku": "any",
  "default_warehouse": "any",
  "epochs": 20,
  "batch_size": 16,
  "learning_rate": 0.001,
  "is_default": true,
  "last_trained": "any",
  "accuracy": "any",
  "dataset_size": "any",
  "date_range": "any",
  "last_updated": "any"
}
```

### 1.6 PUT /api/forecast/models/{model_id}/config
Update Model Config

*Update model configuration.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_id` | `path` | `string` | Yes | - | - |

Request body:
```json
{
  "forecast_horizon": 7,
  "seasonality": "any",
  "validation_split": "any",
  "default_dataset": "any",
  "default_region": "any",
  "default_sku": "any",
  "default_warehouse": "any",
  "epochs": 20,
  "batch_size": 16,
  "learning_rate": 0.001
}
```

Success response:
```json
{
  "id": "string",
  "name": "string",
  "model_type": "transformer",
  "forecast_horizon": 7,
  "seasonality": true,
  "validation_split": 0.0,
  "default_dataset": "any",
  "default_region": "any",
  "default_sku": "any",
  "default_warehouse": "any",
  "epochs": 20,
  "batch_size": 16,
  "learning_rate": 0.001,
  "is_default": true,
  "last_trained": "any",
  "accuracy": "any",
  "dataset_size": "any",
  "date_range": "any",
  "last_updated": "any"
}
```

### 1.7 POST /api/forecast/models/{model_id}/run
Run Model

*Run a specific model directly.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_id` | `path` | `string` | Yes | - | - |
| `forecast_horizon` | `query` | `integer` | No | - | `7` |

Success response:
```json
{
  "type": "object",
  "additionalProperties": true,
  "title": "Response Run Model Api Forecast Models  Model Id  Run Post"
}
```