# Admin Panel Access Guide

This guide explains the complete admin panel connection flow and how to access the admin portal.

## Overview

The admin panel provides a secure, role-based interface for managing the Stratum trading platform. It includes authentication, authorization, and middleware protection to ensure only Super Admin users can access administrative functions.

## Architecture

### Frontend (Next.js)
- **Login Page**: `/admin/login` - Public admin authentication page
- **Admin Portal**: `/admin/*` - Protected admin dashboard and features
- **Middleware**: Validates JWT tokens and enforces Super Admin role
- **API Client**: Handles all backend communication with credentials

### Backend (FastAPI)
- **Auth Endpoints**: Login, logout, and session management
- **Protected Routes**: All admin endpoints require Super Admin role
- **Bootstrap Service**: Auto-creates initial admin user on first startup
- **JWT Authentication**: Cookie-based sessions with role verification

## Connection Flow

```
1. User visits /admin/login
   ↓
2. Middleware checks authentication:
   - No session → Allow access to login page
   - Regular user session → 403 Forbidden
   - Valid admin session → Redirect to /admin/dashboard
   ↓
3. User submits credentials
   ↓
4. Frontend calls POST /api/v1/admin/auth/login
   ↓
5. Backend validates credentials:
   - Checks email/password against database
   - Verifies user has SUPER_ADMIN role
   - Creates JWT token with role claim
   ↓
6. Backend sets secure cookie: stratum_admin_session
   ↓
7. Frontend redirects to /admin/dashboard
   ↓
8. Middleware validates on every request:
   - Extracts JWT from cookie
   - Verifies signature with JWT_SECRET_KEY
   - Confirms role === "SUPER_ADMIN"
   - Allows access if valid, otherwise redirects
   ↓
9. Admin Shell loads and fetches session data
   ↓
10. Protected API calls include cookie automatically
```

## Setup Instructions

### 1. Environment Configuration

Ensure both environment files are properly configured:

**Frontend (`.env.local`)**:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
JWT_SECRET_KEY=<same-as-backend-secret>
```

**Backend (`backend/.env`)**:
```env
DATABASE_URL=postgresql+psycopg://stratum:stratum@localhost:5432/stratum
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<long-random-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=480
COOKIE_SECURE=false
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMe123!
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

**Important**: The `JWT_SECRET_KEY` must match in both files for token verification to work.

### 2. Start Database Services

```bash
docker-compose up -d postgres redis
```

This starts PostgreSQL and Redis containers needed by the backend.

### 3. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

This creates all necessary database tables including the User table.

### 4. Start Backend API

```bash
cd backend
source .venv/bin/activate  # If using virtual environment
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Important**: On first startup, the backend automatically creates the Super Admin user using credentials from `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `backend/.env`. Watch the console output for confirmation:

```
----------------------------------------------------
Initial Super Admin

Email: admin@example.com
Password: ChangeMe123!
----------------------------------------------------
```

### 5. Start Frontend

```bash
npm run dev
```

The Next.js app starts on `http://localhost:3000`.

### 6. Access Admin Panel

1. Navigate to: `http://localhost:3000/admin/login`
2. Enter admin credentials from `backend/.env`:
   - Email: `admin@example.com`
   - Password: `ChangeMe123!`
3. Click "Continue to Admin Portal"
4. You'll be redirected to: `http://localhost:3000/admin/dashboard`

## Security Features

### Middleware Protection
- **Route**: `/admin/login` - Accessible only when not authenticated
- **Route**: `/admin/*` - Protected routes requiring Super Admin role
- **Regular users**: Cannot access admin routes (403 Forbidden)
- **Unauthenticated**: Redirected to login

### Token Verification
The middleware verifies JWT tokens on every request:
```typescript
async function hasValidSuperAdminSession(token: string | undefined) {
  const secret = process.env.JWT_SECRET_KEY;
  if (!token || !secret) return false;
  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(secret));
    return payload.role === "SUPER_ADMIN";
  } catch {
    return false;
  }
}
```

### Backend Authorization
Every protected endpoint uses the `SuperAdmin` dependency:
```python
@router.get("/users", response_model=list[UserOutput])
def list_users(_: SuperAdmin, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))
```

This ensures double verification - both at the Next.js middleware layer and the FastAPI endpoint layer.

## Admin Panel Features

Once authenticated, you have access to:

- **Dashboard** (`/admin/dashboard`) - Overview and system status
- **User Management** (`/admin/users`) - View all registered users
- **Pending Registrations** (`/admin/pending-registrations`) - Review new signups
- **Subscription Approval** (`/admin/subscriptions`) - Approve user subscriptions
- **Connected Users** (`/admin/connected-users`) - Monitor active broker connections
- **Strategies** (`/admin/strategies`) - Upload, start, and stop trading strategies
- **Execution Logs** (`/admin/logs`) - View trading execution history
- **Announcements** (`/admin/announcements`) - Create platform-wide announcements

## Troubleshooting

### Cannot Access Login Page (403 Forbidden)
- **Cause**: You have a regular user session active
- **Solution**: Logout from user account or use incognito mode

### Invalid Credentials Error
- **Cause**: Wrong email/password or admin user not created
- **Solution**: 
  1. Check credentials in `backend/.env`
  2. Restart backend to trigger admin bootstrap
  3. Check backend logs for admin creation message

### Token Verification Failed
- **Cause**: JWT_SECRET_KEY mismatch between frontend and backend
- **Solution**: Ensure `.env.local` and `backend/.env` have identical `JWT_SECRET_KEY`

### Redirect Loop
- **Cause**: Middleware configuration issue or expired token
- **Solution**: 
  1. Clear browser cookies
  2. Check middleware.ts matcher configuration
  3. Verify JWT_EXPIRES_MINUTES is reasonable (default: 480)

### Session Expired
- **Cause**: Token expired (default: 8 hours)
- **Solution**: Login again - sessions expire for security

### CORS Errors
- **Cause**: Frontend origin not in BACKEND_CORS_ORIGINS
- **Solution**: Add `http://localhost:3000` to BACKEND_CORS_ORIGINS in `backend/.env`

## Verification

Run the verification script to check your setup:

```bash
bash verify-admin-flow.sh
```

This script checks:
- Environment files exist and are configured
- Database services are running
- All critical files are present
- Admin credentials are set

## Development Notes

### Cookie Configuration
- **Name**: `stratum_admin_session`
- **HttpOnly**: `true` (prevents JavaScript access)
- **Secure**: Based on `COOKIE_SECURE` env var (false for development)
- **SameSite**: `lax` (CSRF protection)
- **Max Age**: Based on `JWT_EXPIRES_MINUTES`
- **Path**: `/` (available throughout the app)

### JWT Payload
```json
{
  "sub": "user-uuid",
  "role": "SUPER_ADMIN",
  "exp": 1234567890
}
```

### Admin Bootstrap Logic
- Runs on every backend startup
- Only creates admin if no SUPER_ADMIN exists
- Fails if ADMIN_EMAIL belongs to a regular user
- Prints credentials to console for reference

## Security Best Practices

1. **Change Default Credentials**: Update `ADMIN_EMAIL` and `ADMIN_PASSWORD` immediately after first login
2. **Use Strong JWT Secret**: Generate a cryptographically secure random key
3. **Enable HTTPS**: Set `COOKIE_SECURE=true` in production
4. **Regular Session Expiry**: Keep `JWT_EXPIRES_MINUTES` reasonable (default: 8 hours)
5. **Monitor Access**: Check execution logs regularly for admin actions
6. **Limit Admin Accounts**: Only create SUPER_ADMIN accounts when absolutely necessary

## Production Deployment

For production environments:

1. Set `COOKIE_SECURE=true` in `backend/.env`
2. Use HTTPS for both frontend and backend
3. Update `NEXT_PUBLIC_API_BASE_URL` to production API domain
4. Change admin credentials from defaults
5. Use environment-specific secrets (never commit `.env` files)
6. Consider IP whitelisting for admin routes
7. Enable rate limiting on auth endpoints
8. Monitor for suspicious login attempts

---

**Last Updated**: July 20, 2026
