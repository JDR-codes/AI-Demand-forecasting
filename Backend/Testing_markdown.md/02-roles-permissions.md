# Demand Forecasting Backend API Reference — Roles & Permissions

> All endpoints in this module require a super admin user.

## 2. Roles & Permissions

### 2.1 GET /api/roles/roles
List all roles.

Query parameters:
- `skip` (integer, default 0, minimum 0)
- `limit` (integer, default 100, minimum 1, maximum 500)

Success response:
```json
[
  {
    "id": 1,
    "name": "super_admin",
    "description": "Super administrator",
    "created_at": "2026-07-24T10:47:44.218Z",
    "permissions": []
  }
]
```

### 2.2 POST /api/roles/roles
Create a new role.

Request body:
```json
{
  "name": "data_manager",
  "description": "Data source manager",
  "permission_ids": [1, 2, 3]
}
```

Success response (201 Created):
```json
{
  "id": 2,
  "name": "data_manager",
  "description": "Data source manager",
  "created_at": "2026-07-24T10:47:44.226Z",
  "permissions": []
}
```

### 2.3 PUT /api/roles/roles/{role_id}
Update an existing role.

Path parameter:
- `role_id` (integer)

Request body:
```json
{
  "name": "data_manager",
  "description": "Updated description",
  "permission_ids": [1, 4]
}
```

Success response:
```json
{
  "id": 2,
  "name": "data_manager",
  "description": "Updated description",
  "created_at": "2026-07-24T10:47:44.236Z",
  "permissions": []
}
```

### 2.4 DELETE /api/roles/roles/{role_id}
Delete a role.

Path parameter:
- `role_id` (integer)

Success response:
```json
{
  "message": "Role deleted successfully"
}
```

### 2.5 GET /api/roles/permissions
List all permissions.

Success response:
```json
[
  {
    "id": 1,
    "name": "view_data_sources",
    "description": "View data sources"
  }
]
```
