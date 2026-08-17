# Demand Forecasting Backend API Reference — Dashboard

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Dashboard Endpoints

### 1.1 GET /api/dashboard/ai-insights
Get Ai Insights

*GET /api/v1/dashboard/ai-insights

Returns AI-generated insights based on current data:
- Demand trend insights
- Excess/shortage warnings
- Critical alert summaries
- Actionable recommendations
- Priority levels*

Success response:
```json
{
  "insights": [],
  "generated_at": "string"
}
```

### 1.2 GET /api/dashboard/cards
Get Dashboard Cards

*Get dashboard cards data.*

Success response:
```json
{}
```

### 1.3 GET /api/dashboard/demand-trend
Get Demand Trend

*GET /api/v1/dashboard/demand-trend

Returns demand trend analysis:
- Trend points with date, demand, forecast, variance
- Average demand
- Peak demand
- Minimum demand
- Forecast accuracy percentage

Query parameters:
- days: Number of days to analyze (1-365, default 30)*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `days` | `query` | `integer` | No | Number of days to analyze | - |

Success response:
```json
{
  "trend": [],
  "avg_demand": 0.0,
  "peak_demand": 0.0,
  "min_demand": 0.0,
  "forecast_accuracy": 0.0
}
```

### 1.4 GET /api/dashboard/live-alerts
Get Live Alerts

*GET /api/v1/dashboard/live-alerts

Returns live alerts:
- Recent alerts sorted by timestamp
- Alerts grouped by severity (critical, warning, info)
- Unread alert counts
- Alert details (title, message, category, creation time)

Query parameters:
- limit: Maximum number of alerts to return (1-100, default 10)*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `limit` | `query` | `integer` | No | Maximum number of alerts to return | `50` |

Success response:
```json
{
  "alerts": [],
  "critical_count": 1,
  "warning_count": 1,
  "info_count": 1,
  "total_count": 1
}
```

### 1.5 GET /api/dashboard/regional-forecast
Get Regional Forecast

*GET /api/v1/dashboard/regional-forecast

Returns regional forecast data:
- List of forecasts by region and SKU
- Forecasted demand per region
- Confidence scores
- Trend indicators*

Success response:
```json
{
  "forecasts": [],
  "total_regions": 1,
  "timestamp": "string"
}
```

### 1.6 GET /api/dashboard/summary
Get Summary

*GET /api/v1/dashboard/summary

Returns overall dashboard summary metrics:
- Total SKUs
- Total warehouses
- Total forecasts
- Total recommendations
- Critical alerts count
- System health score (0-100)*

Success response:
```json
{
  "metrics": "any",
  "timestamp": "string"
}
```

### 1.7 GET /api/dashboard/top-skus
Get Top Skus

*GET /api/v1/dashboard/top-skus

Returns top SKUs by demand and performance:
- SKU identifier and name
- Total and forecasted demand
- Current stock levels
- Turnover rates
- Revenue impact indicators

Query parameters:
- limit: Maximum number of SKUs to return (1-50, default 10)*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `limit` | `query` | `integer` | No | Maximum number of SKUs to return | `50` |

Success response:
```json
{
  "top_skus": [],
  "timestamp": "string"
}
```

### 1.8 GET /api/dashboard/trends
Get Dashboard Trends

*Get dashboard trend data for charts.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `days` | `query` | `integer` | No | - | - |

Success response:
```json
{}
```

### 1.9 GET /api/dashboard/warehouse-distribution
Get Warehouse Distribution

*GET /api/v1/dashboard/warehouse-distribution

Returns warehouse inventory distribution:
- Current stock levels per warehouse
- Safety stock levels
- Reorder points
- Inventory status (healthy, warning, critical, excess)
- Total stock value*

Success response:
```json
{
  "inventory": [],
  "total_warehouses": 1,
  "total_stock_value": 0.0,
  "timestamp": "string"
}
```