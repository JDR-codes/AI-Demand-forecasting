# Demand Forecasting Backend API Reference — Processing Details

## 7. Processing Details

### 7.1 GET /api/processing/details/{job_id}/outliers
Get outlier results for a processing job.

Path parameter:
- `job_id` (string)

Success response:
```json
{
  "job_id": "proc-job-123",
  "outliers": [
    {
      "column": "quantity",
      "method": "z_score",
      "total_outliers": 5,
      "removed": 2,
      "capped": 1,
      "normal_values": 1194,
      "percentage_removed": 0.17,
      "percentage_capped": 0.08,
      "spike_rows": ["2026-01-10", "2026-01-20"],
      "normal_points": [100, 101, 99],
      "outlier_points": [1000, 1200]
    }
  ],
  "total_columns": 1
}
```

### 7.2 GET /api/processing/details/{job_id}/outliers/chart
Get chart data for a specified outlier column.

Path parameter:
- `job_id` (string)

Query parameter:
- `column` (string, required)

Success response:
```json
{
  "column": "quantity",
  "normal_points": [100, 101, 99],
  "outlier_points": [1000, 1200],
  "spike_rows": ["2026-01-10", "2026-01-20"],
  "total_outliers": 5,
  "normal_count": 1194,
  "removed": 2,
  "capped": 1
}
```

### 7.3 GET /api/processing/details/{job_id}/features
Get generated feature metadata for a processing job.

Path parameter:
- `job_id` (string)

Success response:
```json
{
  "job_id": "proc-job-123",
  "total_features": 12,
  "features": [
    {
      "name": "weekday",
      "type": "temporal",
      "description": "Day of week feature",
      "importance": 0.85,
      "sample_data": [1, 2, 3]
    }
  ],
  "by_type": {
    "temporal": [
      {
        "name": "weekday",
        "description": "Day of week feature",
        "importance": 0.85
      }
    ]
  },
  "feature_importance": {
    "weekday": 0.85
  }
}
```

### 7.4 GET /api/processing/details/{job_id}/logs
Get logs for a processing job.

Path parameter:
- `job_id` (string)

Query parameters:
- `limit` (integer, default 100, max 500)
- `level` (string)

Success response:
```json
{
  "job_id": "proc-job-123",
  "total_logs": 2,
  "logs": [
    {
      "timestamp": "2026-07-24T10:48:00.000Z",
      "level": "INFO",
      "message": "Step completed",
      "step": "ingestion",
      "metadata": {}
    }
  ]
}
```
