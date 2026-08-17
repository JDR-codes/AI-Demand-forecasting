# Demand Forecasting Backend API Reference — Scenarios

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Scenarios Endpoints

### 1.1 GET /api/scenarios
List Scenarios

*List scenarios with filters and pagination.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `page` | `query` | `integer` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |
| `search` | `query` | `any` | No | - | - |
| `status` | `query` | `any` | No | - | - |
| `region` | `query` | `any` | No | - | `"North"` |
| `warehouse` | `query` | `any` | No | - | `"S001"` |
| `category` | `query` | `any` | No | - | `"Electronics"` |
| `sku` | `query` | `any` | No | - | `"P0001"` |
| `sort` | `query` | `string` | No | - | - |

Success response:
```json
{
  "total": 1,
  "page": 1,
  "pages": 1,
  "items": []
}
```

### 1.2 POST /api/scenarios
Create Scenario

*Create a new scenario.*

Request body:
```json
{
  "name": "string",
  "description": "any",
  "region": "North",
  "warehouse": "S001",
  "category": "Electronics",
  "sku": "P0001",
  "time_horizon": 1,
  "demand_surge": 0.0,
  "discount": 0.0,
  "price_change": 0.0,
  "supply_delay": 1,
  "seasonal_impact": 0.0,
  "forecast_model": "string"
}
```

Success response:
```json
{
  "id": 1,
  "name": "string",
  "description": "any",
  "region": "North",
  "warehouse": "S001",
  "category": "Electronics",
  "sku": "P0001",
  "time_horizon": 1,
  "forecast_model": "string",
  "demand_surge": 0.0,
  "discount": 0.0,
  "price_change": 0.0,
  "supply_delay": 1,
  "seasonal_impact": 0.0,
  "status": "any",
  "progress": 0.0,
  "created_by": "any",
  "created_at": "string",
  "updated_at": "string",
  "last_run_at": "any",
  "last_run_status": "any"
}
```

### 1.3 POST /api/scenarios/compare
Compare Scenarios

*Compare multiple scenarios.*

Request body:
```json
{
  "scenario_ids": []
}
```

Success response:
```json
{
  "comparison_id": "string",
  "winner": {},
  "ranking": [],
  "comparison_chart": {},
  "scenario_names": [],
  "created_at": "string"
}
```

### 1.4 GET /api/scenarios/run/{run_id}
Get Progress

*Get simulation progress.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `run_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{
  "run_id": "string",
  "status": "string",
  "progress": 0.0,
  "current_step": "any",
  "step_number": "any",
  "total_steps": "any",
  "message": "any",
  "started_at": "any"
}
```

### 1.5 POST /api/scenarios/run/{run_id}/cancel
Cancel Simulation Run

*Cancel a running simulation.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `run_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.6 GET /api/scenarios/{scenario_id}
Get Scenario

*Get a scenario by ID.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "id": 1,
  "name": "string",
  "description": "any",
  "region": "North",
  "warehouse": "S001",
  "category": "Electronics",
  "sku": "P0001",
  "time_horizon": 1,
  "forecast_model": "string",
  "demand_surge": 0.0,
  "discount": 0.0,
  "price_change": 0.0,
  "supply_delay": 1,
  "seasonal_impact": 0.0,
  "status": "any",
  "progress": 0.0,
  "created_by": "any",
  "created_at": "string",
  "updated_at": "string",
  "last_run_at": "any",
  "last_run_status": "any"
}
```

### 1.7 PUT /api/scenarios/{scenario_id}
Update Scenario

*Update a scenario.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Request body:
```json
{
  "name": "any",
  "description": "any",
  "region": "North",
  "warehouse": "S001",
  "category": "Electronics",
  "sku": "P0001",
  "time_horizon": "any",
  "demand_surge": "any",
  "discount": "any",
  "price_change": "any",
  "supply_delay": "any",
  "seasonal_impact": "any",
  "forecast_model": "any",
  "status": "any"
}
```

Success response:
```json
{
  "id": 1,
  "name": "string",
  "description": "any",
  "region": "North",
  "warehouse": "S001",
  "category": "Electronics",
  "sku": "P0001",
  "time_horizon": 1,
  "forecast_model": "string",
  "demand_surge": 0.0,
  "discount": 0.0,
  "price_change": 0.0,
  "supply_delay": 1,
  "seasonal_impact": 0.0,
  "status": "any",
  "progress": 0.0,
  "created_by": "any",
  "created_at": "string",
  "updated_at": "string",
  "last_run_at": "any",
  "last_run_status": "any"
}
```

### 1.8 DELETE /api/scenarios/{scenario_id}
Delete Scenario

*Delete a scenario.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.9 POST /api/scenarios/{scenario_id}/apply
Apply Scenario Settings

*Promote scenario parameters and execute recommended transfers/reorders.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.10 GET /api/scenarios/{scenario_id}/dashboard
Get Dashboard

*Get complete dashboard data.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "summary_cards": "any",
  "forecast": "any",
  "inventory": "any",
  "stockouts": [],
  "recommendations": []
}
```

### 1.11 GET /api/scenarios/{scenario_id}/export/csv
Export Csv

*Export scenario to CSV.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.12 GET /api/scenarios/{scenario_id}/export/excel
Export Excel

*Export scenario to Excel.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.13 GET /api/scenarios/{scenario_id}/export/pdf
Export Pdf

*Export scenario to PDF.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.14 GET /api/scenarios/{scenario_id}/forecast
Get Forecast Chart

*Get forecast chart data.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "labels": [],
  "baseline": [],
  "simulation": []
}
```

### 1.15 GET /api/scenarios/{scenario_id}/inventory
Get Inventory Chart

*Get inventory chart data.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "labels": [],
  "baseline": [],
  "simulation": []
}
```

### 1.16 GET /api/scenarios/{scenario_id}/recommendations
Get Recommendations

*Get recommendations for a scenario.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
[
  {
    "id": 1,
    "sku": "P0001",
    "title": "string",
    "description": "any",
    "priority": "string",
    "recommendation_type": "string",
    "ai_confidence": "any",
    "estimated_savings": "any",
    "action_label": "any"
  }
]
```

### 1.17 POST /api/scenarios/{scenario_id}/run
Run Scenario

*Run a scenario simulation asynchronously.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "run_id": "string",
  "scenario_id": 1,
  "status": "string",
  "progress": 0.0,
  "step": "any",
  "step_number": "any",
  "total_steps": "any",
  "started_at": "any"
}
```

### 1.18 GET /api/scenarios/{scenario_id}/runs
Get Scenario Run History

*Get the history of simulation runs for a scenario.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
[
  {
    "run_id": "string",
    "status": "string",
    "progress": 0.0,
    "current_step": "any",
    "step_number": "any",
    "total_steps": "any",
    "message": "any",
    "started_at": "any"
  }
]
```

### 1.19 GET /api/scenarios/{scenario_id}/stockouts
Get Stockouts

*Get stockout table data.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
[
  {
    "sku": "P0001",
    "product_name": "any",
    "demand": 0.0,
    "shortage": 0.0,
    "revenue_risk": 0.0,
    "risk_level": "string",
    "current_stock": "any",
    "recommended_quantity": "any",
    "lost_sales": "any"
  }
]
```