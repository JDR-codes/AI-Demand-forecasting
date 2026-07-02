# AI Demand Forecasting Platform — Complete Testing Guide

## How to Use This Guide

1. Start the server and authenticate (Prerequisites section below)
2. Follow each module section in order — some modules depend on data created in earlier ones
3. Use the request payloads exactly as shown — copy-paste into Swagger's request body box
4. Check the Expected Response after each call to confirm it worked

---

## Prerequisites — Do This Before Testing Anything

### 1. Start the Server

```bash
uvicorn fastapi_app.main:app --reload
```

Open Swagger at: `http://127.0.0.1:8000/docs`

### 2. Bootstrap the Super Admin (one time only)

**Endpoint:** `POST /api/v1/auth/super-admin/setup`

**Request Body:**
```json
{
  "name": "Root Admin",
  "email": "admin@example.com",
  "password": "AdminPass1"
}
```

**Expected:** 200 OK with user object

**Note:** If you see 403 "Super admin already exists" — skip this step and proceed to login

### 3. Login and Authorize

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "admin@example.com",
  "password": "AdminPass1"
}
```

**Expected:** 200 OK with `access_token`, `refresh_token`, and user object

**Steps:**
1. Copy the `access_token` value
2. Click **Authorize 🔒** (top right of Swagger)
3. Paste the token → Click Authorize
4. **Note:** Re-authorize every time the token expires (60 minutes by default)

---

## Module 1 — Authentication (`/api/v1/auth`)

### GET /api/v1/auth/me — Get Current User

**Steps:** Execute with no body (uses your token)

**Expected 200 OK:**
```json
{
  "id": 1,
  "name": "Root Admin",
  "email": "admin@example.com",
  "role": "super_admin",
  "is_active": true,
  "created_at": "2026-06-22T..."
}
```

### POST /api/v1/auth/refresh-token — Refresh Access Token

**Request Body:**
```json
{
  "refresh_token": "<paste refresh_token from login response>"
}
```

**Expected 200 OK:** New `access_token` issued

### POST /api/v1/auth/logout — Logout

**Steps:** Execute with no body (uses your token)

**Expected 200 OK:**
```json
{
  "message": "Logged out successfully"
}
```

### Password Reset Flow (3 steps)

#### Step 1 — POST /api/v1/auth/forgot-password

**Request Body:**
```json
{
  "email": "admin@example.com"
}
```

**Expected 200 OK:**
```json
{
  "message": "An OTP has been sent to your email address.",
  "reset_token": null,
  "otp_code": null
}
```

**Note:** Requires SMTP credentials in `.env`. If not configured, you'll get a 400 with a clear error message.
For testing without email, check the `otp_records` table in `test.db` directly for the generated OTP code.

#### Step 2 — POST /api/v1/auth/verify-otp

**Request Body:**
```json
{
  "email": "admin@example.com",
  "otp_code": "123456"
}
```

**Expected 200 OK:**
```json
{
  "message": "OTP verified successfully. Use the reset_token to set your new password.",
  "reset_token": "eyJ..."
}
```

**Expected failure cases:**
- Wrong OTP → 400 Bad Request with "Invalid OTP"
- Expired OTP (after 10 min) → 400 Bad Request with "OTP has expired"

#### Step 3 — POST /api/v1/auth/reset-password

**Request Body:**
```json
{
  "email": "admin@example.com",
  "reset_token": "<paste reset_token from step 2>",
  "new_password": "NewPass123"
}
```

**Expected 200 OK:**
```json
{
  "message": "Password has been reset successfully. You can now log in."
}
```

**Verify:** Log in again with NewPass123

**Password validation rules:**
- Minimum 8 characters → 422 if shorter
- At least one uppercase letter → 422 if missing
- At least one digit → 422 if missing

---

## Module 4 — Roles & Permissions (`/api/v1/roles`, `/api/v1/permissions`)

**Note:** All endpoints require `super_admin` token

### GET /api/v1/permissions — List All Permissions

**Steps:** Execute with no body

**Expected 200 OK — 14 permissions:**
```json
[
  { "id": 1,  "name": "users:read",           "description": "View user accounts" },
  { "id": 2,  "name": "users:write",          "description": "Create or update user accounts" },
  { "id": 3,  "name": "users:delete",         "description": "Delete user accounts" },
  { "id": 4,  "name": "roles:read",           "description": "View roles and their permissions" },
  { "id": 5,  "name": "roles:write",          "description": "Create or update roles" },
  { "id": 6,  "name": "roles:delete",         "description": "Delete roles" },
  { "id": 7,  "name": "data:read",            "description": "View data sources and uploaded datasets" },
  { "id": 8,  "name": "data:write",           "description": "Upload or modify data sources and datasets" },
  { "id": 9,  "name": "forecast:read",        "description": "View forecasts and trained models" },
  { "id": 10, "name": "forecast:run",         "description": "Train models and generate forecasts" },
  { "id": 11, "name": "recommendations:read", "description": "View generated recommendations" },
  { "id": 12, "name": "validation:read",      "description": "View data validation results" },
  { "id": 13, "name": "inventory:read",       "description": "View inventory, stock, and reorder data" },
  { "id": 14, "name": "inventory:write",      "description": "Modify inventory, transfers, and reorder points" }
]
```

**Note:** Save the IDs — you'll need them when creating roles.

### GET /api/v1/roles — List All Roles

**Expected 200 OK — 2 seeded default roles:**
```json
[
  {
    "id": 1,
    "name": "super_admin",
    "description": "Full access to every resource in the system.",
    "created_at": "...",
    "permissions": [ "...all 14 permissions..." ]
  },
  {
    "id": 2,
    "name": "user",
    "description": "Default role for newly created accounts. No elevated permissions.",
    "created_at": "...",
    "permissions": []
  }
]
```

### POST /api/v1/roles — Create a Role

**Request Body:**
```json
{
  "name": "manager",
  "description": "Access to forecasting and data",
  "permission_ids": [7, 8, 9, 10]
}
```

**Expected 201 Created:**
```json
{
  "id": 3,
  "name": "manager",
  "description": "Access to forecasting and data",
  "created_at": "...",
  "permissions": [
    { "id": 7,  "name": "data:read",     "description": "..." },
    { "id": 8,  "name": "data:write",    "description": "..." },
    { "id": 9,  "name": "forecast:read", "description": "..." },
    { "id": 10, "name": "forecast:run",  "description": "..." }
  ]
}
```

**Note:** Save the `id` (e.g., 3) for use in PUT and DELETE tests

**Failure cases:**
- Duplicate name → 409 with "A role with this name already exists"
- Invalid permission ID (e.g., 999) → 409 with "permission_ids not found: [999]"

### PUT /api/v1/roles/{role_id} — Update a Role

Set `role_id = 3` (the manager role created above)

**Test A — Rename only:**
```json
{ "name": "senior_manager" }
```
Expected: 200 OK — name updated, permissions unchanged

**Test B — Replace permissions:**
```json
{ "permission_ids": [1, 2, 3] }
```
Expected: 200 OK — now has only users:read, users:write, users:delete

**Test C — Nonexistent role:**
Set `role_id = 9999` → 404 Not Found

### DELETE /api/v1/roles/{role_id} — Delete a Role

Set `role_id = 3` → Expected 200 OK:
```json
{ "message": "Role deleted successfully" }
```

**Guard rail tests:**
- Delete your own role (`role_id = 1`) → 400 Bad Request with "You cannot delete the role currently assigned to your own account."
- Delete a role that still has users on it → 409 Conflict with user count in message

---

## Module 6 — Data Sources (`/api/v1/data-sources`)

**Requires:** Login (any role)

### POST /api/v1/data-sources/ — Create Data Source

**Request Body:**
```json
{
  "name": "Main CSV Source",
  "type": "csv",
  "connection_string": "fastapi_app/data/demand forecasting dataset.csv"
}
```

**Expected 200 OK** with `id`, `status: "inactive"`, `health: "unknown"`

**Note:** Save the `id` returned — use it for all subsequent data source tests

### GET /api/v1/data-sources/ — List All Data Sources

**Expected 200 OK:** Array of data source objects

### GET /api/v1/data-sources/{data_source_id} — Get One

**Expected 200 OK:** Single data source object

**Nonexistent ID → 404 Not Found**

### PUT /api/v1/data-sources/{data_source_id} — Update

**Request Body:**
```json
{
  "name": "Updated CSV Source",
  "status": "active"
}
```

**Expected 200 OK** with updated fields

### POST /api/v1/data-sources/{data_source_id}/sync — Trigger Sync

**Expected 200 OK** — `last_sync` timestamp updated

### POST /api/v1/data-sources/{data_source_id}/schedule-sync — Schedule Sync

**Expected 200 OK** — sync scheduled

### GET /api/v1/data-sources/{data_source_id}/health — Health Check

**Expected 200 OK** — health status object

### GET /api/v1/data-sources/{data_source_id}/logs — View Logs

**Expected 200 OK** — array of log entries

### DELETE /api/v1/data-sources/{data_source_id} — Delete

**Expected 200 OK:**
```json
{ "deleted": true }
```

---

## Module 7 — File Uploads (`/api/v1/uploads`)

### POST /api/v1/uploads/file — Upload a CSV

**Steps:**
1. Expand the endpoint in Swagger
2. Click "Try it out"
3. Under "file", click "Choose File" and select your `demand forecasting dataset.csv`
4. Click "Execute"

**Expected 200 OK:**
```json
{
  "id": 1,
  "filename": "demand forecasting dataset.csv",
  "file_path": "...",
  "status": "uploaded",
  "uploaded_by": "admin@example.com",
  "created_at": "..."
}
```

**Failure:** Uploading a non-CSV file → 400 Bad Request with "Only CSV files are accepted"

### GET /api/v1/uploads/ — List All Uploads

**Expected 200 OK:** Array of upload records

### GET /api/v1/uploads/{upload_id} — Get One Upload

**Expected 200 OK:** Single upload record

**Nonexistent ID → 404 Not Found**

### POST /api/v1/uploads/{upload_id}/process — Process Upload

**Expected 200 OK** — status changes to `processed`

### DELETE /api/v1/uploads/{upload_id} — Delete Upload

**Expected 200 OK:**
```json
{ "deleted": true }
```

---

## Module 8 — Data Processing (`/api/v1/processing`)

### POST /api/v1/processing/start — Start Pipeline

**Steps:** Execute with no body

**Expected 200 OK** — pipeline started response

### GET /api/v1/processing/pipeline — Pipeline Status

**Expected 200 OK** — pipeline status and stage info

### GET /api/v1/processing/outliers — Detect Outliers

**Expected 200 OK** — list of detected outliers

### GET /api/v1/processing/features — Feature Engineering

**Expected 200 OK** — feature list

### GET /api/v1/processing/logs — Processing Logs

**Expected 200 OK** — array of log entries

### POST /api/v1/processing/stop — Stop Pipeline

**Expected 200 OK** — pipeline stopped

---

## Module 9 — Forecast Engine (`/api/v1/forecast`)

**Note:** This module requires a dataset uploaded first (Module 7). The CSV must have `Date` and `Demand` columns.

### POST /api/v1/forecast/models — Register a Model

**Request Body:**
```json
{
  "name": "ARIMA Model v1",
  "model_type": "arima",
  "version": "1.0"
}
```

**Expected 200 OK** with model object containing `model_id`

**Note:** Save the `model_id` for subsequent tests

### GET /api/v1/forecast/models — List All Models

**Expected 200 OK:** Array of registered model objects

### PUT /api/v1/forecast/models/{model_id} — Update Model

**Request Body:**
```json
{
  "name": "ARIMA Model v2",
  "model_type": "arima",
  "version": "2.0"
}
```

**Expected 200 OK** — updated model

**Nonexistent ID → 404 Not Found**

### POST /api/v1/forecast/train — Train a Model

**Request Body:**
```json
{
  "model_type": "arima",
  "csv_path": "fastapi_app/data/demand forecasting dataset.csv",
  "steps": 7,
  "order": [1, 1, 1]
}
```

**Model type options:** `arima`, `xgboost`, `lstm`, `prophet`

**Expected 200 OK:**
```json
{
  "job_id": "...",
  "model_type": "arima",
  "status": "completed",
  "created_at": "...",
  "metrics": {
    "mse": "...",
    "rmse": "...",
    "mae": "...",
    "mape": "..."
  }
}
```

**Note:** Save the `job_id` returned

### GET /api/v1/forecast/train/{job_id} — Check Training Job Status

**Expected 200 OK** — job details including status and metrics

### POST /api/v1/forecast/generate — Generate a Forecast

**Request Body:**
```json
{
  "sku": "SKU-001",
  "region": "North",
  "warehouse": "WH-A",
  "horizon": 7,
  "model_used": "arima"
}
```

**Expected 200 OK** — forecast record with `predicted_demand` and `confidence_score`

**Note:** Save the `id` returned

### GET /api/v1/forecast/results — List All Forecasts

**Expected 200 OK:** Array of forecast records

### GET /api/v1/forecast/results/{forecast_id} — Get One Forecast

**Expected 200 OK:** Single forecast record

**Nonexistent ID → 404 Not Found**

### GET /api/v1/forecast/metrics — Get All Model Metrics

**Expected 200 OK** — metrics for all trained models

### GET /api/v1/forecast/metrics/{model_type} — Get Metrics by Model Type

Set `model_type` to `arima`, `xgboost`, `lstm`, or `prophet`

**Expected 200 OK** — metrics for that specific model type

### POST /api/v1/forecast/retrain — Retrain a Specific Model

**Request Body:**
```json
{
  "model_type": "arima",
  "csv_path": "fastapi_app/data/demand forecasting dataset.csv",
  "steps": 7,
  "order": [1, 1, 1]
}
```

**Expected 200 OK** — new training job initiated

### POST /api/v1/forecast/retrain-all — Retrain All Models

**Steps:** Execute with no body

**Expected 200 OK** — all models retrained

### POST /api/v1/forecast/retrain/{job_id} — Check Retrain Job

**Expected 200 OK** — retrain job status

### DELETE /api/v1/forecast/models/{model_id} — Delete Model

**Expected 200 OK:**
```json
{ "message": "Model deleted successfully" }
```

---

## Module 9b — Forecast Engine Report (`/api/v1/forecast-engine`)

### GET /api/v1/forecast-engine/report — Run Full AI Forecast Report

**Parameters:**
- `path`: Full absolute path to your CSV file (e.g., `C:\Users\kizan\...\demand forecasting dataset.csv`)
- `forecast_steps`: Number of days to forecast (default 7)

**Expected 200 OK** (takes 10–30 seconds to train all 4 models):
```json
{
  "series_length": 730,
  "arima": {
    "forecast": [171.2, 174.6, 176.3, "..."],
    "peaks": [
      { "step": 2, "value": 174.6 },
      "..."
    ],
    "model_stats": {
      "aic": "...",
      "bic": "..."
    }
  },
  "xgboost": {
    "model_type": "xgboost",
    "metrics": {
      "mse": "...",
      "rmse": "...",
      "mae": "..."
    },
    "future_predictions": ["..."]
  },
  "lstm": { "..." },
  "prophet": { "..." }
}
```

**Note:** If you get a 500 TypeError, open `forecast_service.py` line ~94 and change `.fillna(method="bfill").fillna(method="ffill")` → `.bfill().ffill()` (pandas 3.x compatibility fix)

---

## Module 10 — Recommendations (`/api/v1/recommendations`)

### POST /api/v1/recommendations — Create a Recommendation

**Request Body:**
```json
{
  "sku": "SKU-001",
  "warehouse": "WH-A",
  "region": "North",
  "recommendation_type": "reorder",
  "priority": "high",
  "title": "Reorder SKU-001",
  "description": "Stock will reach reorder point in 3 days",
  "recommended_action": "Place order for 500 units",
  "quantity": 500,
  "estimated_cost": 25000.0,
  "potential_savings": 3500.0
}
```

**Expected 200 OK** with `id` and `status: "pending"`

### GET /api/v1/recommendations — List All

**Expected 200 OK:** Array of recommendation objects

### GET /api/v1/recommendations/critical — Critical Recommendations

**Expected 200 OK** — only critical-priority items

### GET /api/v1/recommendations/high — High Priority

**Expected 200 OK** — only high-priority items

### GET /api/v1/recommendations/reorder — Reorder Recommendations

**Expected 200 OK** — only reorder-type items

### GET /api/v1/recommendations/procurement — Procurement Recommendations

**Expected 200 OK** — only procurement-type items

### GET /api/v1/recommendations/{recommendation_id} — Get One

**Expected 200 OK** — single recommendation

**Nonexistent ID → 404 Not Found**

### PUT /api/v1/recommendations/{recommendation_id} — Update

**Request Body:**
```json
{
  "priority": "critical",
  "description": "Updated: stockout imminent"
}
```

**Expected 200 OK** — updated recommendation

### POST /api/v1/recommendations/{recommendation_id}/execute — Execute

**Expected 200 OK** — status changes to `executed`

### POST /api/v1/recommendations/{recommendation_id}/ignore — Ignore

**Expected 200 OK** — status changes to `ignored`

### POST /api/v1/recommendations/execute-all — Execute All

**Expected 200 OK:**
```json
{
  "executed_count": 1,
  "message": "..."
}
```

### POST /api/v1/recommendations/ignore-all — Ignore All

**Expected 200 OK:**
```json
{
  "ignored_count": 1,
  "message": "..."
}
```

### GET /api/v1/recommendations/stats/overview — Stats Overview

**Expected 200 OK** — counts by status and priority

### DELETE /api/v1/recommendations/{recommendation_id} — Delete

**Expected 200 OK:**
```json
{ "deleted": true }
```

---

## Module 11 — Inventory Optimization (`/api/v1/inventory`)

**Important:** Seed sample data first — otherwise all GET endpoints return empty results.

### POST /api/v1/inventory/seed-sample-data — Seed Test Data

**Steps:** Execute with no body

**Expected 200 OK:**
```json
{
  "message": "Sample inventory data seeded successfully",
  "skus_created": 3,
  "warehouse_records_created": 9
}
```

This creates 3 SKUs across 3 warehouses in 2 regions. Run all subsequent tests after this.

### GET /api/v1/inventory/health — Overall Inventory Health

**Expected 200 OK:**
```json
{
  "health_score": 72,
  "status": "at_risk",
  "total_skus": 3,
  "at_risk_skus": 1,
  "critical_skus": 0,
  "metrics": {
    "stock_turnover_ratio": 4.2,
    "fill_rate_percentage": 95.0,
    "excess_stock_percentage": 18.5,
    "stockout_risk_count": 1
  }
}
```

### GET /api/v1/inventory/safety-stock — Safety Stock Analysis

**Query param:** `service_level` — valid values: `90`, `95`, `97`, `99`, `99.9` (default `95`)

**Expected 200 OK** — safety stock per SKU per warehouse with current vs recommended comparison

**Failure:** Invalid service level (e.g., 85) → 400 Bad Request

### GET /api/v1/inventory/reorder-points — Reorder Points

**Expected 200 OK** — each SKU/warehouse shows:
- `reorder_point_value`
- `reorder_status`: `URGENT_ORDER_NOW`, `PLANNED_REORDER`, or `SAFE`
- `days_until_stockout`
- `economic_order_quantity`

### GET /api/v1/inventory/transfers — Transfer Recommendations

**Expected 200 OK** — recommended stock moves between warehouses with:
- `from_warehouse` / `to_warehouse`
- `transfer_quantity`
- `transfer_cost`
- `potential_cost_savings`
- `roi_percentage`
- `priority`: `high`, `medium`, or `low`

### GET /api/v1/inventory/excess-stock — Excess Stock Analysis

**Expected 200 OK** — items with too much stock showing:
- `excess_quantity`
- `days_inventory_on_hand`
- `excess_level`: `critical`, `high`, `medium`, or `low`
- `action_recommended`: `aggressive_discount`, `transfer`, `clearance`, or `donation`
- `total_carrying_cost`

---

## Module 12 — Scenario Simulation (`/api/v1/scenarios`)

### POST /api/v1/scenarios — Create a Scenario

**Request Body — Test A:**
```json
{
  "name": "Holiday Demand Surge",
  "description": "Simulate 30% demand increase during holiday season",
  "parameters": {
    "demand_multiplier": 1.3,
    "duration_days": 30,
    "affected_skus": ["SKU-001", "SKU-002"]
  }
}
```

**Request Body — Test B:**
```json
{
  "name": "Forecast scenario",
  "description": "Forecast with arima and generate recommendations",
  "parameters": {
    "model_type": "arima",
    "csv_path": "C:\\Users\\kizan\\OneDrive\\Desktop\\AIDFP_final\\AIDFP_updated\\fastapi_app\\uploads\\demand forecasting dataset.csv",
    "forecast_steps": 7,
    "recommendation_k": 3,
    "sku": "SKU-10",
    "region": "North",
    "warehouse": "WH-01"
  }
}
```

**Expected 200 OK** with `id` and `status: "created"`

### GET /api/v1/scenarios — List All Scenarios

**Expected 200 OK:** Array of scenario objects

### GET /api/v1/scenarios/{scenario_id} — Get One

**Expected 200 OK:** Single scenario

**Nonexistent ID → 404 Not Found**

### PUT /api/v1/scenarios/{scenario_id} — Update

**Request Body:**
```json
{
  "name": "Holiday Surge — Updated",
  "parameters": {
    "demand_multiplier": 1.5,
    "duration_days": 45
  }
}
```

**Expected 200 OK** — updated scenario

### POST /api/v1/scenarios/{scenario_id}/run — Run the Scenario

**Steps:** Execute with no body

**Expected 200 OK** — status changes to `completed`, `last_run_at` populated, `last_run_output` contains results

### DELETE /api/v1/scenarios/{scenario_id} — Delete

**Expected 200 OK:**
```json
{ "deleted": true }
```

---

## Module 13 — Alerts (`/api/v1/alerts`)

### POST /api/v1/alerts — Create an Alert

**Request Body:**
```json
{
  "title": "Low Stock Warning",
  "message": "SKU-001 at WH-A has fallen below safety stock level",
  "severity": "warning",
  "category": "inventory",
  "sku": "SKU-001",
  "warehouse": "WH-A",
  "region": "North"
}
```

**Severity options:** `info`, `warning`, `critical`

**Category options:** `inventory`, `forecast`, `reorder`, `excess_stock`, `transfer`, `system`

**Expected 201 Created** with full alert object

### GET /api/v1/alerts — List All Alerts

**Optional filters** (add as query params):
- `severity=critical`
- `category=inventory`
- `is_read=false`
- `skip=0` / `limit=50`

**Expected 200 OK:**
```json
{
  "total": 1,
  "unread": 1,
  "items": [
    {
      "id": 1,
      "title": "...",
      "severity": "warning",
      "is_read": false,
      "..."
    }
  ]
}
```

### PATCH /api/v1/alerts/{alert_id}/read — Mark as Read

**Expected 200 OK:**
```json
{
  "id": 1,
  "is_read": true,
  "message": "Alert marked as read"
}
```

### DELETE /api/v1/alerts/{alert_id} — Delete Alert

**Expected 200 OK:**
```json
{
  "id": 1,
  "message": "Alert deleted successfully"
}
```

---

## Module 14 — Reports (`/api/v1/reports`)

### POST /api/v1/reports/generate — Generate a Report

**Test A — Forecast Summary:**
```json
{
  "title": "Weekly Forecast Report",
  "report_type": "forecast_summary",
  "format": "json",
  "parameters": { "limit": 50 }
}
```

**Test B — Inventory Health Report:**
```json
{
  "title": "Inventory Health Report",
  "report_type": "inventory_health",
  "format": "json"
}
```

**Test C — Full System Report:**
```json
{
  "title": "Full System Report",
  "report_type": "full_system",
  "format": "json"
}
```

**Report type options:**
- `forecast_summary` — all forecasts
- `inventory_health` — stock, reorder points, excess, transfers, safety stock
- `recommendation_summary` — procurement/reorder recommendations
- `scenario_comparison` — all scenarios with run outputs
- `full_system` — all four combined with executive summary

**Format options:** `json` or `csv`

**Expected 200 OK** — fully populated report object with `data` field containing the report content

**Failure:** Invalid `report_type` → 422 Unprocessable Entity

### GET /api/v1/reports — List All Reports

**Expected 200 OK:** Array of report summaries (newest first)

### GET /api/v1/reports/{report_id} — Get Full Report

**Expected 200 OK:** Complete report including data payload

**Nonexistent ID → 404 Not Found**

### GET /api/v1/reports/{report_id}/download — Download Report

**Expected:** File download attachment
- `format: "json"` → downloads as `.json` file
- `format: "csv"` → downloads as `.csv` file

---

## Module 15 — Dashboard (`/api/v1/dashboard`)

**Note:** Requires inventory data seeded (Module 11) and forecasts generated (Module 9) for meaningful results. Returns empty/zero values otherwise — not an error.

### GET /api/v1/dashboard/summary — Overall Summary

**Expected 200 OK:**
```json
{
  "total_skus": 3,
  "total_warehouses": 3,
  "total_forecasts": 1,
  "total_recommendations": 1,
  "critical_alerts": 0,
  "system_health_score": 85
}
```

### GET /api/v1/dashboard/demand-trend — Demand Trend

**Query param:** `days` (1–365, default 30)

**Expected 200 OK:**
```json
{
  "trend": [
    {
      "date": "2026-05-23",
      "demand": 185.2,
      "forecast": 183.4,
      "variance": 1.8
    },
    "..."
  ],
  "avg_demand": 190.5,
  "peak_demand": 346.1,
  "min_demand": 100.2,
  "forecast_accuracy": 94.3
}
```

### GET /api/v1/dashboard/regional-forecast — Regional Forecast

**Expected 200 OK** — forecasts grouped by region with trend indicators

### GET /api/v1/dashboard/warehouse-distribution — Warehouse Distribution

**Expected 200 OK** — stock levels per warehouse with status indicators

### GET /api/v1/dashboard/ai-insights — AI Insights

**Expected 200 OK** — actionable AI-generated insights based on current data

### GET /api/v1/dashboard/live-alerts — Live Alerts

**Query param:** `limit` (1–100, default 10)

**Expected 200 OK** — recent alerts sorted by timestamp

### GET /api/v1/dashboard/top-skus — Top SKUs

**Query param:** `limit` (1–50, default 10)

**Expected 200 OK** — top SKUs by demand with turnover rates

---

## Module 16 — Validation (`/api/v1/validation`)

**Note:** Validation errors are auto-generated when the data pipeline runs. If no errors exist, the list will be empty.

### GET /api/v1/validation/errors — List All Errors

**Expected 200 OK:** Array of validation errors (may be empty on a fresh DB)

### GET /api/v1/validation/errors/{error_id} — Get One Error

**Expected 200 OK:** Single error

**Nonexistent ID → 404 Not Found**

### POST /api/v1/validation/errors/{error_id}/fix — Fix an Error

**Request Body:**
```json
{ "resolution": "Filled missing values with interpolation" }
```

**Expected 200 OK** — status changes to `fixed`

### POST /api/v1/validation/errors/{error_id}/ignore — Ignore an Error

**Expected 200 OK** — status changes to `ignored`

### POST /api/v1/validation/fix-all — Fix All Errors

**Expected 200 OK:**
```json
{ "fixed_count": 2 }
```

---

## Error Reference — All Modules

| Status | Meaning | When it happens |
|--------|---------|-----------------|
| 401 Unauthorized | No or invalid token | Missing Authorization header or expired token |
| 403 Forbidden | Wrong role | Non-super_admin calling a super_admin endpoint |
| 404 Not Found | Resource missing | ID doesn't exist in the database |
| 400 Bad Request | Business rule violation | Invalid OTP, self-lockout prevention, invalid service level |
| 409 Conflict | Duplicate or constraint | Duplicate role name, role has users assigned |
| 422 Unprocessable Entity | Validation failed | Wrong field types, missing required fields, password too weak |
| 500 Internal Server Error | Server-side crash | Check the uvicorn terminal for the full traceback |

---

## Recommended Test Order (Full System)

Run these in sequence for a complete end-to-end test session:

1. **Auth** — Bootstrap super admin → Login → Get token
2. **Roles** — List permissions → Create manager role → Verify GET
3. **Data Sources** — Create → Sync → Health check
4. **Uploads** — Upload CSV → Process
5. **Inventory** — Seed data → Health → Safety stock → Reorder points → Transfers → Excess
6. **Forecast** — Register model → Train (arima) → Generate forecast → View results → Forecast engine report
7. **Recommendations** — Create → Execute → View stats
8. **Scenarios** — Create → Run → View output
9. **Alerts** — Create (critical) → Mark read → Verify unread count
10. **Dashboard** — Summary → Demand trend → Warehouse distribution → AI insights
11. **Reports** — Generate full_system → Download as JSON → Generate inventory_health as CSV
12. **Auth** — Password Reset — Forgot password → Verify OTP → Reset → Login with new password

---

## Quick Checklist

- [ ] Super admin setup returns 200, second attempt returns 403
- [ ] Login returns access_token and refresh_token
- [ ] `/auth/me` returns correct user with `role: "super_admin"`
- [ ] 14 permissions listed in `GET /permissions`
- [ ] `POST /roles` creates with correct permissions assigned
- [ ] `DELETE /roles/1` (own role) blocked with 400
- [ ] Inventory seed returns `skus_created: 3`, `warehouse_records_created: 9`
- [ ] Safety stock rejects invalid service level with 400
- [ ] Reorder points show `URGENT_ORDER_NOW`, `PLANNED_REORDER`, or `SAFE` statuses
- [ ] Forecast training returns metrics (MSE, RMSE, MAE)
- [ ] Forecast engine report runs all 4 models and returns combined output
- [ ] Scenario run changes status to `completed` and populates `last_run_output`
- [ ] Alert creation accepts all severity/category enum values
- [ ] Report `full_system` type returns all 4 sections
- [ ] Report download returns file attachment
- [ ] Dashboard summary reflects seeded data counts
- [ ] Password reset flow completes and new password works for login
