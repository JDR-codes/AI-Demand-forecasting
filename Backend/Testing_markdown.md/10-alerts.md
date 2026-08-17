# Demand Forecasting Backend API Reference — Alerts

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Alerts Endpoints

### 1.1 GET /api/alerts
Get Alerts

*List all alerts — filter by severity, category, is_read*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `severity` | `query` | `any` | No | info | warning | critical | - |
| `category` | `query` | `any` | No | inventory | forecast | reorder | excess_stock | transfer | system | `"Electronics"` |
| `is_read` | `query` | `any` | No | true | false | - |
| `skip` | `query` | `integer` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |

Success response:
```json
{
  "total": 1,
  "unread": 1,
  "items": []
}
```

### 1.2 POST /api/alerts
Create Alert

*Create a new alert*

Request body:
```json
{
  "title": "string",
  "message": "string",
  "severity": "any",
  "category": "Electronics",
  "sku": "P0001",
  "warehouse": "S001",
  "region": "North"
}
```

Success response:
```json
{
  "id": 1,
  "title": "string",
  "message": "string",
  "severity": "any",
  "category": "Electronics",
  "sku": "P0001",
  "warehouse": "S001",
  "region": "North",
  "is_read": true,
  "created_at": "string",
  "updated_at": "string"
}
```

### 1.3 DELETE /api/alerts/{alert_id}
Delete Alert

*Permanently delete an alert*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alert_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "id": 1,
  "message": "string"
}
```

### 1.4 PATCH /api/alerts/{alert_id}/read
Mark Alert Read

*Mark a specific alert as read*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alert_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{
  "id": 1,
  "is_read": true,
  "message": "string"
}
```