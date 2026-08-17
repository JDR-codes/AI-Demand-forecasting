# Demand Forecasting Backend API Reference — Reports

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Reports Endpoints

### 1.1 GET /api/reports
List Reports

*GET /api/v1/reports

Return all previously generated reports (newest first), optionally filtered by search query or category/type.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `search` | `query` | `any` | No | - | - |
| `category` | `query` | `any` | No | - | `"Electronics"` |
| `skip` | `query` | `integer` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |

Success response:
```json
[
  {
    "id": 1,
    "title": "string",
    "description": "any",
    "report_type": "string",
    "status": "string",
    "format": "string",
    "file_size": "any",
    "page_count": "any",
    "generated_at": "any",
    "created_at": "string"
  }
]
```

### 1.2 POST /api/reports/generate
Generate Report

*POST /api/reports/generate

report_type options:
- `executive_summary` — high-level KPIs and insights only
- `demand_summary` — demand overview, trends, key drivers
- `forecast_summary` — all forecasts (filter by sku / warehouse / region)
- `model_performance` — accuracy and diagnostics per forecasting model
- `inventory_health` — warehouse stock, reorder points, excess stock, transfers, safety stock
- `stockout_risk` — at-risk SKUs and recommendations
- `recommendation_summary` — procurement/reorder recommendations (filter by status / priority)
- `scenario_comparison` — all scenarios with run outputs and side-by-side comparison
- `full_system` — all sections combined with an executive summary
- `custom_report` — pass `parameters.sections` to pick which sections to include

format: `json` (default) | `csv` | `pdf` | `excel`

parameters examples:
```json
{
  "sku": "SKU-001",
  "region": "West",
  "category": "Electronics",
  "date_range": "last_30_days",
  "limit": 50
}
```*

Request body:
```json
{
  "title": "any",
  "description": "any",
  "report_type": "string",
  "format": "any",
  "parameters": "any"
}
```

Success response:
```json
{
  "id": 1,
  "title": "string",
  "description": "any",
  "report_type": "string",
  "status": "string",
  "format": "string",
  "file_size": "any",
  "page_count": "any",
  "parameters": "any",
  "data": "any",
  "summary": "any",
  "generated_by": "any",
  "generated_at": "any",
  "error_message": "any",
  "created_at": "string",
  "updated_at": "string"
}
```

### 1.3 GET /api/reports/overview-metrics
Get Overview Metrics

*GET /api/reports/overview-metrics?region=West&category=Electronics&date_range=last_30_days

Live KPI cards for the Reports landing page header
(Total Revenue Impact, Average Forecast Accuracy, Stockouts Prevented,
Overstock Reduced) — computed fresh from current DB state, independent
of any specific generated report. All filters are optional.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `region` | `query` | `any` | No | - | `"North"` |
| `category` | `query` | `any` | No | - | `"Electronics"` |
| `date_range` | `query` | `any` | No | - | - |

Success response:
```json
{
  "type": "object",
  "additionalProperties": true,
  "title": "Response Get Overview Metrics Api Reports Overview Metrics Get"
}
```

### 1.4 GET /api/reports/sku-details/{sku}
Get Sku Details

*GET /api/reports/sku-details/{sku}

Get detailed analysis of a single SKU.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `sku` | `path` | `string` | Yes | - | `"P0001"` |

Success response:
```json
{
  "sku": "P0001",
  "product": "string",
  "revenue": 0.0,
  "units_sold": 1,
  "forecast_accuracy": 0.0,
  "yoy_change": 0.0,
  "demand_forecast_12m": [],
  "accuracy_trend_12m": [],
  "sales_by_region": {},
  "stock_by_warehouse": {},
  "monthly_performance": []
}
```

### 1.5 GET /api/reports/sku-performance
Get Sku Performance

*GET /api/reports/sku-performance

Get SKU performance statistics for SKU reports grid tab.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `search` | `query` | `any` | No | - | - |

Success response:
```json
[
  {
    "sku": "P0001",
    "product": "string",
    "revenue": 0.0,
    "units_sold": 1,
    "forecast_accuracy": 0.0,
    "yoy_change": 0.0
  }
]
```

### 1.6 GET /api/reports/{report_id}
Get Report

*GET /api/v1/reports/{report_id}

Retrieve a specific report by id including its full data payload.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `report_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "id": 1,
  "title": "string",
  "description": "any",
  "report_type": "string",
  "status": "string",
  "format": "string",
  "file_size": "any",
  "page_count": "any",
  "parameters": "any",
  "data": "any",
  "summary": "any",
  "generated_by": "any",
  "generated_at": "any",
  "error_message": "any",
  "created_at": "string",
  "updated_at": "string"
}
```

### 1.7 GET /api/reports/{report_id}/download
Download Report

*GET /api/v1/reports/{report_id}/download

Download the report as a file attachment. Supports format overrides (pdf, excel, csv, json).*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `report_id` | `path` | `integer` | Yes | - | - |
| `format` | `query` | `any` | No | - | - |

Success response:
```json
{}
```