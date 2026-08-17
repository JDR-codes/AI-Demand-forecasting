# Demand Forecasting Backend API Reference — Scheduler

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Scheduler Endpoints

### 1.1 GET /api/scheduler/frequencies
Get Valid Frequencies

*Get valid frequency options.*

Success response:
```json
{}
```

### 1.2 GET /api/scheduler/jobs
Get Scheduled Jobs

*Get all scheduled jobs with next run times.*

Success response:
```json
{}
```

### 1.3 GET /api/scheduler/jobs/sync
Get Scheduled Sync Jobs

*Get all scheduled sync jobs.*

Success response:
```json
{}
```

### 1.4 GET /api/scheduler/jobs/training
Get Scheduled Training Jobs

*Get all scheduled training jobs.*

Success response:
```json
{}
```

### 1.5 GET /api/scheduler/jobs/{job_id}
Get Scheduled Job

*Get a specific scheduled job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.6 DELETE /api/scheduler/jobs/{job_id}
Delete Scheduled Job

*Delete a scheduled job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.7 POST /api/scheduler/jobs/{job_id}/pause
Pause Scheduled Job

*Pause a scheduled job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.8 POST /api/scheduler/jobs/{job_id}/resume
Resume Scheduled Job

*Resume a paused scheduled job.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.9 POST /api/scheduler/jobs/{job_id}/run-now
Run Scheduled Job Now

*Execute a scheduled job immediately.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```