# Demand Forecasting Backend API Reference — Recommendations

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Recommendations Endpoints

### 1.1 GET /api/recommendations/
List Recommendations

*List recommendations with filters and pagination.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `status` | `query` | `any` | No | - | - |
| `priority` | `query` | `any` | No | - | - |
| `recommendation_type` | `query` | `any` | No | - | - |
| `category` | `query` | `any` | No | - | `"Electronics"` |
| `sku` | `query` | `any` | No | - | `"P0001"` |
| `warehouse` | `query` | `any` | No | - | `"S001"` |
| `region` | `query` | `any` | No | - | `"North"` |
| `search` | `query` | `any` | No | - | - |
| `page` | `query` | `integer` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |

Success response:
```json
{}
```

### 1.3 GET /api/recommendations/dashboard
Get Dashboard

*Get recommendation dashboard statistics.*

Success response:
```json
{}
```

### 1.4 GET /api/recommendations/dashboard/trend
Get Trend Data

*Get trend data for charts.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `days` | `query` | `integer` | No | - | - |

Success response:
```json
{}
```

### 1.5 POST /api/recommendations/execute-all
Execute All

*Execute all recommendations by filter.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `filter_type` | `query` | `string` | No | all, critical, high, medium, reorder, procurement | - |

Success response:
```json
{}
```

### 1.6 GET /api/recommendations/executed
Get Executed

*Get executed recommendations.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `limit` | `query` | `integer` | No | - | `50` |

Success response:
```json
{}
```

### 1.7 GET /api/recommendations/forecast/{forecast_job_id}
Get Forecast Recommendations

*Get recommendations for a specific forecast.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `forecast_job_id` | `path` | `string` | Yes | - | - |

Success response:
```json
{}
```

### 1.8 POST /api/recommendations/generate
Generate Recommendations

*Generate recommendations from a completed forecast.
This is the main entry point - no background jobs.*

Request body:
```json
{
  "forecast_job_id": "string"
}
```

Success response:
```json
{
  "success": true,
  "message": "string",
  "count": 1,
  "recommendations": []
}
```

### 1.10 GET /api/recommendations/history
Get History

*Get recommendation history.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `recommendation_id` | `query` | `any` | No | - | - |
| `action` | `query` | `any` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |
| `offset` | `query` | `integer` | No | - | - |

Success response:
```json
{}
```

### 1.11 POST /api/recommendations/ignore-all
Ignore All

*Ignore all recommendations by filter.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `filter_type` | `query` | `string` | No | all, critical, high, medium, reorder, procurement | - |
| `reason` | `query` | `any` | No | - | - |

Success response:
```json
{}
```

### 1.12 GET /api/recommendations/ignored
Get Ignored

*Get ignored recommendations.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `limit` | `query` | `integer` | No | - | `50` |

Success response:
```json
{}
```

### 1.13 GET /api/recommendations/pending
Get Pending

*Get pending recommendations.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `page` | `query` | `integer` | No | - | - |
| `limit` | `query` | `integer` | No | - | `50` |

Success response:
```json
{}
```

### 1.14 GET /api/recommendations/summary
Get Summary

*Get summary for execute dialog.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `filter_type` | `query` | `string` | No | all, critical, high, medium, reorder, procurement | - |

Success response:
```json
{}
```

### 1.15 GET /api/recommendations/{recommendation_id}
Get Recommendation

*Get a specific recommendation with details.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `recommendation_id` | `path` | `integer` | Yes | - | - |

Success response:
```json
{}
```

### 1.16 POST /api/recommendations/{recommendation_id}/execute
Execute Recommendation

*Execute a recommendation.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `recommendation_id` | `path` | `integer` | Yes | - | - |

Request body:
```json
{
  "notes": "any"
}
```

Success response:
```json
{}
```

### 1.17 POST /api/recommendations/{recommendation_id}/ignore
Ignore Recommendation

*Ignore a recommendation.*

Parameters:
| Name | In | Type | Required | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `recommendation_id` | `path` | `integer` | Yes | - | - |

Request body:
```json
{
  "reason": "any"
}
```

Success response:
```json
{}
```