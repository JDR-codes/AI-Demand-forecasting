# Demand Forecasting Backend API Reference — Processing

## 6. Processing

### 6.1 GET /api/processing/dashboard
Get processing dashboard with latest job summary.

Success response:
```json
{
  "title": "Data Processing",
  "subtitle": "Data cleaning, transformation, feature engineering pipeline",
  "job_id": "proc-job-123",
  "summary": {
    "steps_complete": 4,
    "total_steps": 7,
    "records_processed": 1200,
    "outliers_detected": 15,
    "pipeline_duration": "00:12:30",
    "status": "running",
    "current_step": "feature_engineering",
    "progress_percentage": 57,
    "message": "Processing data"
  },
  "steps": [
    {
      "step_number": 1,
      "name": "ingestion",
      "status": "completed",
      "progress": 100,
      "records_processed": 1200,
      "started_at": "2026-07-24T10:40:00Z",
      "completed_at": "2026-07-24T10:41:00Z",
      "duration": "00:01:00",
      "message": "Ingested raw data"
    }
  ],
  "tabs": ["Pipeline", "Outliers", "Feature Engineering", "Logs"],
  "actions": {
    "pause_enabled": true,
    "rerun_enabled": true
  }
}
```

### 6.2 POST /api/processing/start
Start a new processing job.

Request body:
```json
{
  "upload_id": 1,
  "dataset_path": "sales_data.csv"
}
```

Success response:
```json
{
  "id": 1,
  "job_id": "proc-job-123",
  "upload_id": 1,
  "dataset_path": "sales_data.csv",
  "status": "queued",
  "progress_percentage": 0,
  "current_step": "ingestion",
  "records_loaded": 1200,
  "records_processed": 0,
  "records_failed": 0,
  "started_at": "2026-07-24T10:47:44.445Z",
  "completed_at": null,
  "paused_at": null,
  "duration_seconds": 0,
  "eta_seconds": 1200,
  "error_message": null,
  "created_at": "2026-07-24T10:47:44.445Z"
}
```

### 6.3 GET /api/processing/jobs/{job_id}
Get a processing job by ID.

Path parameter:
- `job_id` (string)

Success response:
```json
{
  "id": 1,
  "job_id": "proc-job-123",
  "upload_id": 1,
  "dataset_path": "sales_data.csv",
  "status": "queued",
  "progress_percentage": 0,
  "current_step": "ingestion",
  "records_loaded": 1200,
  "records_processed": 0,
  "records_failed": 0,
  "started_at": "2026-07-24T10:47:44.452Z",
  "completed_at": null,
  "paused_at": null,
  "duration_seconds": 0,
  "eta_seconds": 1200,
  "error_message": null,
  "created_at": "2026-07-24T10:47:44.452Z"
}
```

### 6.4 GET /api/processing/jobs/{job_id}/steps
Get processing job steps.

Path parameter:
- `job_id` (string)

Success response:
```json
[
  {
    "id": 1,
    "step_number": 1,
    "step_name": "ingestion",
    "status": "completed",
    "progress": 100,
    "records_processed": 1200,
    "started_at": "2026-07-24T10:47:44.459Z",
    "completed_at": "2026-07-24T10:48:00.000Z",
    "duration_seconds": 16.0,
    "message": "Data ingestion complete"
  }
]
```

### 6.5 POST /api/processing/jobs/{job_id}/pause
Pause a processing job.

Path parameter:
- `job_id` (string)

Success response:
```json
{
  "message": "Job paused"
}
```

### 6.6 POST /api/processing/jobs/{job_id}/resume
Resume a paused job.

Path parameter:
- `job_id` (string)

Success response:
```json
{
  "message": "Job resumed"
}
```

### 6.7 POST /api/processing/jobs/{job_id}/cancel
Cancel a processing job.

Path parameter:
- `job_id` (string)

Success response:
```json
{
  "message": "Job cancelled"
}
```

### 6.8 POST /api/processing/jobs/{job_id}/restart
Restart a processing job from the same upload.

Path parameter:
- `job_id` (string)

Success response:
```json
{
  "message": "Job restarted",
  "new_job_id": "proc-job-124"
}
```
