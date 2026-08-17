# Demand Forecasting Backend API Reference — Notifications

## 8. Notifications

### 8.1 GET /api/notifications/
Get notifications with optional filters.

Query parameters:
- `limit` (integer, default 50, max 100)
- `offset` (integer, default 0)
- `status` (string)
- `priority` (string)
- `notification_type` (string)
- `search` (string)

Success response:
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Forecast completed",
    "message": "Your forecast job has finished.",
    "type": "forecast",
    "priority": "high",
    "status": "unread",
    "entity_type": "forecast",
    "entity_id": "job-123",
    "created_at": "2026-07-24T10:47:44.533Z",
    "read_at": null
  }
]
```

### 8.2 GET /api/notifications/list
Get notifications with pagination.

Query parameters:
- `page` (integer, default 1)
- `limit` (integer, default 20, max 100)
- `status` (string)
- `priority` (string)
- `notification_type` (string)
- `search` (string)

Success response:
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "title": "Forecast completed",
      "message": "Your forecast job has finished.",
      "type": "forecast",
      "priority": "high",
      "status": "unread",
      "entity_type": "forecast",
      "entity_id": "job-123",
      "created_at": "2026-07-24T10:47:44.547Z",
      "read_at": null
    }
  ],
  "total": 1,
  "unread_count": 1,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

### 8.3 GET /api/notifications/unread
Get unread notification count.

Success response:
```json
{
  "unread_count": 3
}
```

### 8.4 PATCH /api/notifications/read-all
Mark all notifications as read.

Success response:
```json
{
  "message": "3 notifications marked as read",
  "count": 3
}
```

### 8.5 PATCH /api/notifications/{notification_id}
Mark a notification as read.

Path parameter:
- `notification_id` (integer)

Success response:
```json
{
  "id": 1,
  "status": "read",
  "message": "Notification marked as read"
}
```

### 8.6 DELETE /api/notifications/{notification_id}
Delete/archive a notification.

Path parameter:
- `notification_id` (integer)

Success response:
```json
{
  "message": "Notification deleted"
}
```

### 8.7 DELETE /api/notifications/{notification_id}/permanent
Permanently delete a notification.

Path parameter:
- `notification_id` (integer)

Success response:
```json
{
  "message": "Notification permanently deleted"
}
```
