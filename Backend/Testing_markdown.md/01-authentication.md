# Demand Forecasting Backend API Reference — Authentication

## Base URLs
- Local dev server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication Scheme
This application uses JWT access tokens for API authentication.
- `Authorization: Bearer <access_token>` header for protected endpoints.
- Refresh token stored in HTTP-only cookie `refresh_token`.
- Access token is also stored in cookie `access_token`.

---

## 1. Authentication Endpoints

### 1.1 POST /api/auth/super-admin/setup
Create the initial super admin user.

Request body:
```json
{
  "name": "Admin User",
  "email": "admin@example.com",
  "password": "StrongPass123",
  "confirm_password": "StrongPass123",
  "role": "super_admin"
}
```

Success response:
```json
{
  "id": 1,
  "name": "Admin User",
  "email": "admin@example.com",
  "role": "super_admin",
  "is_active": true,
  "created_at": "2026-07-24T10:47:43.826Z"
}
```

### 1.2 POST /api/auth/login
Login with email and password.

Request body:
```json
{
  "email": "admin@example.com",
  "password": "StrongPass123"
}
```

Success response:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "Admin User",
    "email": "admin@example.com",
    "role": "super_admin",
    "is_active": true,
    "created_at": "2026-07-24T10:47:44.173Z"
  },
  "refresh_token": "eyJhbGciOi..."
}
```

### 1.3 POST /api/auth/logout
Logout the current user and revoke the refresh token.

Headers:
- `Authorization: Bearer <access_token>`

Success response:
```json
{
  "message": "Logged out successfully"
}
```

### 1.4 POST /api/auth/refresh-token
Rotate refresh token and get a fresh access token.

The endpoint reads the refresh token from the `refresh_token` cookie.

Success response:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "Admin User",
    "email": "admin@example.com",
    "role": "super_admin",
    "is_active": true,
    "created_at": "2026-07-24T10:47:44.183Z"
  },
  "refresh_token": "eyJhbGciOi..."
}
```

### 1.5 POST /api/auth/forgot-password
Request password reset OTP.

Request body:
```json
{
  "email": "user@example.com"
}
```

Success response:
```json
{
  "message": "OTP sent successfully",
  "reset_token": "abc123...",
  "otp_code": "654321"
}
```

### 1.6 POST /api/auth/verify-otp
Verify the OTP and receive a reset token.

Request body:
```json
{
  "email": "user@example.com",
  "otp_code": "654321"
}
```

Success response:
```json
{
  "message": "OTP verified successfully. Use the reset_token to set your new password.",
  "reset_token": "abc123...",
  "otp_code": "654321"
}
```

### 1.7 POST /api/auth/reset-password
Reset a password using the reset token.

Request body:
```json
{
  "email": "user@example.com",
  "reset_token": "abc123...",
  "new_password": "NewStrongPass123",
  "confirm_new_password": "NewStrongPass123"
}
```

Success response:
```json
{
  "message": "Password reset successfully"
}
```

### 1.8 GET /api/auth/me
Get the authenticated current user.

Headers:
- `Authorization: Bearer <access_token>`

Success response:
```json
{
  "id": 1,
  "name": "Admin User",
  "email": "admin@example.com",
  "role": "super_admin",
  "is_active": true,
  "created_at": "2026-07-24T10:47:44.211Z"
}
```
