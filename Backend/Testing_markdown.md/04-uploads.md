# Demand Forecasting Backend API Reference — Uploads

## 4. Uploads

### 4.1 POST /api/uploads/
Upload a single file.

Form field:
- `file` (multipart file) with extension `.csv`, `.xlsx`, `.xls`, or `.json`

Success response:
```json
{
  "id": 1,
  "filename": "sales_data.csv",
  "unique_filename": "sales_data_20260724_1.csv",
  "file_path": "/media/uploads/sales_data_20260724_1.csv",
  "file_url": "http://localhost:8000/media/uploads/sales_data_20260724_1.csv",
  "status": "uploaded",
  "uploaded_by": 1,
  "uploaded_at": "2026-07-24T10:47:44.337Z",
  "file_size": 254321,
  "rows": 1200,
  "columns": 12,
  "processing_progress": 0.0,
  "processing_status": "pending",
  "duration_seconds": 0.0
}
```

### 4.2 POST /api/uploads/multiple
Upload multiple files by multipart values or file path strings.

Form fields:
- `files` (list of string file paths or multipart file uploads)
- `file_paths` (string list of local file paths)

Example multi-file JSON body accepted by the endpoint:
```json
{
  "files": ["/tmp/sales1.csv", "/tmp/sales2.csv"]
}
```

Success response:
```json
[
  {
    "id": 1,
    "filename": "sales1.csv",
    "unique_filename": "sales1_20260724_1.csv",
    "file_path": "/media/uploads/sales1_20260724_1.csv",
    "file_url": "http://localhost:8000/media/uploads/sales1_20260724_1.csv",
    "status": "uploaded",
    "uploaded_by": 1,
    "uploaded_at": "2026-07-24T10:47:44.357Z",
    "file_size": 254321,
    "rows": 1200,
    "columns": 12,
    "processing_progress": 0.0,
    "processing_status": "pending",
    "duration_seconds": 0.0
  }
]
```

### 4.3 GET /api/uploads/
List uploads with optional filters.

Query parameters:
- `status` (string)
- `limit` (integer, default 50, max 100)
- `offset` (integer, default 0)

Success response:
```json
[
  {
    "id": 1,
    "filename": "sales_data.csv",
    "unique_filename": "sales_data_20260724_1.csv",
    "file_path": "/media/uploads/sales_data_20260724_1.csv",
    "file_url": "http://localhost:8000/media/uploads/sales_data_20260724_1.csv",
    "status": "uploaded",
    "uploaded_by": 1,
    "uploaded_at": "2026-07-24T10:47:44.348Z",
    "file_size": 254321,
    "rows": 1200,
    "columns": 12,
    "processing_progress": 0.0,
    "processing_status": "pending",
    "duration_seconds": 0.0
  }
]
```

### 4.4 GET /api/uploads/stats
Get upload statistics.

Success response:
```json
{
  "total": 10,
  "pending": 2,
  "processed": 7,
  "failed": 1,
  "total_size_bytes": 10485760,
  "total_size_mb": 10.0
}
```

### 4.5 GET /api/uploads/{upload_id}
Get details for an upload.

Path parameter:
- `upload_id` (integer)

Success response:
```json
{
  "id": 1,
  "filename": "sales_data.csv",
  "unique_filename": "sales_data_20260724_1.csv",
  "file_path": "/media/uploads/sales_data_20260724_1.csv",
  "file_url": "http://localhost:8000/media/uploads/sales_data_20260724_1.csv",
  "status": "uploaded",
  "uploaded_by": 1,
  "uploaded_at": "2026-07-24T10:47:44.366Z",
  "file_size": 254321,
  "rows": 1200,
  "columns": 12,
  "processing_progress": 0.0,
  "processing_status": "pending",
  "duration_seconds": 0.0
}
```

### 4.6 DELETE /api/uploads/{upload_id}
Delete an upload.

Path parameter:
- `upload_id` (integer)

Success response:
```json
{
  "deleted": true
}
```

### 4.7 GET /api/uploads/{upload_id}/preview
Preview upload rows.

Path parameter:
- `upload_id` (integer)

Query parameters:
- `rows` (integer, default 20, max 100)

Success response:
```json
{
  "columns": ["date", "sku", "quantity", "price"],
  "rows": [
    {"date": "2026-01-01", "sku": "A123", "quantity": 10, "price": 99.99},
    {"date": "2026-01-02", "sku": "A123", "quantity": 12, "price": 99.99}
  ],
  "row_count": 1200,
  "upload_id": 1,
  "filename": "sales_data.csv"
}
```
