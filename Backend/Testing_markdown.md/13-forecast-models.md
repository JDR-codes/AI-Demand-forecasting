# Demand Forecasting Backend API Reference — Forecast Models

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Forecast Models Endpoints

### 1.1 GET /api/forecast/models/
List Models

*List all registered forecast models with metrics.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `active_only` | `query` | `boolean` | No | - | - |

Success response:
```json
[
  {
    "id": "string",
    "name": "string",
    "model_type": "transformer",
    "version": "string",
    "is_default": true,
    "is_active": true,
    "is_favorite": true,
    "deployment_status": "string",
    "last_trained": "any",
    "training_size": "any",
    "best_accuracy": "any",
    "best_rmse": "any",
    "best_mae": "any",
    "best_mape": "any",
    "best_r2": "any",
    "best_loss": "any",
    "framework": "any",
    "algorithm": "any",
    "hyperparameters": "any",
    "feature_set": "any",
    "artifact_path": "any",
    "artifact_size": "any",
    "training_duration": "any",
    "framework_version": "any",
    "status": "string",
    "description": "any",
    "archived_at": "any",
    "production_version": "any",
    "production_deployed_at": "any",
    "created_at": "string"
  }
]
```

### 1.2 GET /api/forecast/models/{model_id}
Get Model

*Get a specific model with full metrics.*

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
  "version": "string",
  "is_default": true,
  "is_active": true,
  "is_favorite": true,
  "deployment_status": "string",
  "last_trained": "any",
  "training_size": "any",
  "best_accuracy": "any",
  "best_rmse": "any",
  "best_mae": "any",
  "best_mape": "any",
  "best_r2": "any",
  "best_loss": "any",
  "framework": "any",
  "algorithm": "any",
  "hyperparameters": "any",
  "feature_set": "any",
  "artifact_path": "any",
  "artifact_size": "any",
  "training_duration": "any",
  "framework_version": "any",
  "status": "string",
  "description": "any",
  "archived_at": "any",
  "production_version": "any",
  "production_deployed_at": "any",
  "created_at": "string"
}
```

### 1.3 PUT /api/forecast/models/{model_id}
Update Model

*Update model status (activate/deactivate).*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_id` | `path` | `string` | Yes | - | - |
| `is_active` | `query` | `boolean` | Yes | - | - |

Success response:
```json
{}
```

### 1.4 DELETE /api/forecast/models/{model_id}
Delete Model

*Delete a registered model.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.5 POST /api/forecast/models/{model_id}/promote
Promote Model

*Promote a model version to be default/active.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```