# Demand Forecasting Backend API Reference — Inventory

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Inventory Endpoints

### 1.1 GET /api/inventory/alerts
Get Inventory Alerts

*Get inventory alerts.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `is_read` | `query` | `any` | No | - | - |
| `severity` | `query` | `any` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |
| `offset` | `query` | `integer` | No | - | - |

Success response:
```json
{}
```

### 1.2 POST /api/inventory/alerts/{alert_id}/mark-read
Mark Alert Read

*Mark an alert as read.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alert_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.3 GET /api/inventory/dashboard
Get Inventory Dashboard

*Get the complete inventory dashboard in one request.*

Success response:
```json
{
  "health_cards": "any",
  "reorder_points": [],
  "excess_inventory": [],
  "slow_moving_items": [],
  "warehouse_distribution": [],
  "inventory_value_distribution": [],
  "warehouse_summary": [],
  "transfer_recommendations": [],
  "timestamp": "string"
}
```

### 1.4 GET /api/inventory/export
Export Inventory Report

*Export inventory report.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `format` | `query` | `string` | No | - | - |

Success response:
```json
{}
```

### 1.5 POST /api/inventory/transfers
Create Manual Stock Transfer

*Manually create and execute a stock transfer between warehouses.*

Request body:
```json
{
  "sku": "P0001",
  "from_warehouse": "string",
  "to_warehouse": "string",
  "quantity": 0.0,
  "priority": "string"
}
```

Success response:
```json
{}
```

### 1.6 GET /api/inventory/transfers
Get Stock Transfers List

*Get the log history of warehouse stock transfers.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `status` | `query` | `any` | No | - | - |

Success response:
```json
[
  {
    "id": 1,
    "sku": "P0001",
    "from_warehouse": "string",
    "to_warehouse": "string",
    "transfer_quantity": 0.0,
    "priority": "string",
    "status": "string",
    "created_at": "string"
  }
]
```

### 1.7 POST /api/inventory/transfers/{transfer_id}/approve
Approve Transfer Recommendation

*Approve and execute a warehouse stock transfer recommendation.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `transfer_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.8 POST /api/inventory/update-stock
Update Stock

*Update inventory stock level.*

Request body:
```json
{
  "sku": "P0001",
  "warehouse": "S001",
  "new_quantity": 0.0,
  "reason": "string"
}
```

Success response:
```json
{
  "success": true,
  "sku": "P0001",
  "warehouse": "S001",
  "old_quantity": 0.0,
  "new_quantity": 0.0,
  "change": 0.0,
  "inventory_value": "any",
  "message": "string"
}
```