# Demand Forecasting Backend API Reference — Data Sources

## 3. Data Sources

### 3.1 GET /api/data-sources/dashboard
Get data source dashboard metrics.

Success response:
```json
{
  "total_records": 12345,
  "active_connections": 5,
  "total_connections": 7,
  "sync_frequency": "daily",
  "validation_errors": 2,
  "health_percentage": 85,
  "today_syncs": 3,
  "today_failed_syncs": 0,
  "today_successful_syncs": 3,
  "recent_uploads": 4,
  "recent_validations": 8,
  "timestamp": "2026-07-24T10:44:31.568452"
}
```

### 3.2 GET /api/data-sources/
List all data sources.

Success response:
```json
[
  {
    "name": "Sales API",
    "type": "API",
    "provider": "SAP",
    "base_url": "https://sales.example.com/api",
    "connection_string": "",
    "api_key": "abc123",
    "username": "user1",
    "password": "secret",
    "bucket_name": "",
    "folder_path": "",
    "table_name": "sales_data",
    "sync_frequency": "manual",
    "id": 1,
    "status": "active",
    "health": "good",
    "last_sync": "2026-07-24T10:47:44.253Z",
    "created_at": "2026-07-24T10:47:44.253Z",
    "record_count": 2000,
    "health_score": 95.0,
    "last_sync_duration": 12.4,
    "next_sync": "2026-07-25T00:00:00Z",
    "last_error": ""
  }
]
```

### 3.3 POST /api/data-sources/
Create a new data source.

Request body:
```json
{
  "name": "Sales API",
  "type": "API",
  "provider": "SAP",
  "base_url": "https://sales.example.com/api",
  "connection_string": "",
  "api_key": "abc123",
  "username": "user1",
  "password": "secret",
  "bucket_name": "",
  "folder_path": "",
  "table_name": "sales_data",
  "sync_frequency": "manual"
}
```

Success response:
```json
{
  "name": "Sales API",
  "type": "API",
  "provider": "SAP",
  "base_url": "https://sales.example.com/api",
  "connection_string": "",
  "api_key": "abc123",
  "username": "user1",
  "password": "secret",
  "bucket_name": "",
  "folder_path": "",
  "table_name": "sales_data",
  "sync_frequency": "manual",
  "id": 1,
  "status": "active",
  "health": "good",
  "last_sync": "2026-07-24T10:47:44.261Z",
  "created_at": "2026-07-24T10:47:44.261Z",
  "record_count": 2000,
  "health_score": 95.0,
  "last_sync_duration": 12.4,
  "next_sync": "2026-07-25T00:00:00Z",
  "last_error": ""
}
```

### 3.4 GET /api/data-sources/{data_source_id}
Get a data source by ID.

Path parameter:
- `data_source_id` (integer)

Success response:
```json
{
  "name": "Sales API",
  "type": "API",
  "provider": "SAP",
  "base_url": "https://sales.example.com/api",
  "connection_string": "",
  "api_key": "abc123",
  "username": "user1",
  "password": "secret",
  "bucket_name": "",
  "folder_path": "",
  "table_name": "sales_data",
  "sync_frequency": "manual",
  "id": 1,
  "status": "active",
  "health": "good",
  "last_sync": "2026-07-24T10:47:44.269Z",
  "created_at": "2026-07-24T10:47:44.269Z",
  "record_count": 2000,
  "health_score": 95.0,
  "last_sync_duration": 12.4,
  "next_sync": "2026-07-25T00:00:00Z",
  "last_error": ""
}
```

### 3.5 PUT /api/data-sources/{data_source_id}
Update a data source.

Path parameter:
- `data_source_id` (integer)

Request body:
```json
{
  "name": "Sales API",
  "type": "API",
  "provider": "SAP",
  "base_url": "https://sales.example.com/api",
  "connection_string": "",
  "api_key": "abc123",
  "username": "user1",
  "password": "newsecret",
  "bucket_name": "",
  "folder_path": "",
  "table_name": "sales_data",
  "status": "active",
  "health": "good",
  "sync_frequency": "daily"
}
```

Success response:
```json
{
  "name": "Sales API",
  "type": "API",
  "provider": "SAP",
  "base_url": "https://sales.example.com/api",
  "connection_string": "",
  "api_key": "abc123",
  "username": "user1",
  "password": "newsecret",
  "bucket_name": "",
  "folder_path": "",
  "table_name": "sales_data",
  "sync_frequency": "daily",
  "id": 1,
  "status": "active",
  "health": "good",
  "last_sync": "2026-07-24T10:47:44.281Z",
  "created_at": "2026-07-24T10:47:44.281Z",
  "record_count": 2000,
  "health_score": 95.0,
  "last_sync_duration": 12.4,
  "next_sync": "2026-07-25T00:00:00Z",
  "last_error": ""
}
```

### 3.6 DELETE /api/data-sources/{data_source_id}
Delete a data source.

Path parameter:
- `data_source_id` (integer)

Success response:
```json
{
  "deleted": true
}
```

### 3.7 POST /api/data-sources/{data_source_id}/sync
Start a manual sync for a data source.

Path parameter:
- `data_source_id` (integer)

Success response:
```json
{
  "message": "Sync job started",
  "job_id": "sync-job-123",
  "status": "queued"
}
```

### 3.8 POST /api/data-sources/sync-all
Sync all configured data sources.

Success response:
```json
{
  "message": "Started sync for 3 data sources",
  "job_ids": ["sync-job-123", "sync-job-124", "sync-job-125"]
}
```

### 3.9 POST /api/data-sources/{data_source_id}/schedule
Schedule a data source sync.

Path parameter:
- `data_source_id` (integer)

Query parameter:
- `frequency` (required; one of `manual`, `hourly`, `daily`, `weekly`, `monthly`, `realtime`)

Success response:
```json
{
  "message": "Data source scheduled with frequency: daily",
  "data_source": {
    "name": "Sales API",
    "type": "API",
    "provider": "SAP",
    "base_url": "https://sales.example.com/api",
    "connection_string": "",
    "api_key": "abc123",
    "username": "user1",
    "password": "newsecret",
    "bucket_name": "",
    "folder_path": "",
    "table_name": "sales_data",
    "sync_frequency": "daily",
    "id": 1,
    "status": "active",
    "health": "good",
    "last_sync": "2026-07-24T10:47:44.281Z",
    "created_at": "2026-07-24T10:47:44.281Z",
    "record_count": 2000,
    "health_score": 95.0,
    "last_sync_duration": 12.4,
    "next_sync": "2026-07-25T00:00:00Z",
    "last_error": ""
  }
}
```

### 3.10 PUT /api/data-sources/{data_source_id}/schedule
Update an existing data source schedule.

Path parameter:
- `data_source_id` (integer)

Query parameter:
- `frequency` (required; same valid values)

Success response:
```json
{
  "message": "Data source schedule updated to: weekly",
  "data_source": {...}
}
```

### 3.11 DELETE /api/data-sources/{data_source_id}/schedule
Remove schedule from a data source.

Path parameter:
- `data_source_id` (integer)

Success response:
```json
{
  "message": "Schedule removed",
  "data_source_id": 1
}
```

### 3.12 GET /api/data-sources/{data_source_id}/health
Get the health status for a data source.

Path parameter:
- `data_source_id` (integer)

Success response:
```json
{
  "job_id": "...",
  "health": "good"
}
```
