# Admin Panel - Quick Start Guide

## 🚀 Fast Setup (5 Steps)

```bash
# 1. Start database services
docker-compose up -d postgres redis

# 2. Run migrations
cd backend && alembic upgrade head

# 3. Start backend (creates admin user automatically)
cd backend && uvicorn app.main:app --reload

# 4. Start frontend (in new terminal)
npm run dev

# 5. Access admin panel
# Open: http://localhost:3000/admin/login
```

## 🔐 Default Credentials

```
Email: admin@example.com
Password: ChangeMe123!
```

*These are set in `backend/.env` - change them after first login!*

## 📋 Verification Checklist

Run the verification script:
```bash
bash verify-admin-flow.sh
```

Manual checklist:
- [ ] Docker services running (postgres, redis)
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Both `.env` files have matching `JWT_SECRET_KEY`
- [ ] Admin user created (check backend console output)

## 🔄 Complete Connection Flow

```mermaid
graph TD
    A[Visit /admin/login] --> B{Middleware Check}
    B -->|No session| C[Show Login Form]
    B -->|Regular user| D[403 Forbidden]
    B -->|Valid admin| E[Redirect to Dashboard]
    
    C --> F[Submit Credentials]
    F --> G[POST /api/v1/admin/auth/login]
    G --> H{Backend Validates}
    
    H -->|Invalid| I[401 Error]
    H -->|Not Super Admin| J[403 Error]
    H -->|Valid| K[Create JWT Token]
    
    K --> L[Set Cookie: stratum_admin_session]
    L --> M[Redirect to /admin/dashboard]
    M --> N[Middleware Verifies JWT]
    N --> O[Load Admin Shell]
    O --> P[Fetch Session Data]
    P --> Q[Render Dashboard]
```

## 🛠️ Common Commands

### Check if services are running
```bash
# Check PostgreSQL
docker ps | grep postgres

# Check Redis  
docker ps | grep redis

# Check backend
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000
```

### Restart services
```bash
# Restart databases
docker-compose restart postgres redis

# Restart backend
cd backend && uvicorn app.main:app --reload

# Restart frontend
npm run dev
```

### View logs
```bash
# Docker container logs
docker-compose logs -f postgres
docker-compose logs -f redis

# Backend logs (in backend terminal)
# Frontend logs (in npm terminal)
```

## 🔍 Troubleshooting Quick Fixes

### Issue: Cannot access login page (403)
```bash
# Solution: Clear cookies or use incognito mode
# Cause: Regular user session conflicts with admin
```

### Issue: Invalid credentials
```bash
# Check credentials in backend/.env
cat backend/.env | grep ADMIN

# Restart backend to recreate admin
# Check backend console for admin creation message
```

### Issue: Token verification failed
```bash
# Verify JWT secrets match
echo "Frontend:" && cat .env.local | grep JWT_SECRET_KEY
echo "Backend:" && cat backend/.env | grep JWT_SECRET_KEY

# They must be identical!
```

### Issue: CORS errors
```bash
# Check BACKEND_CORS_ORIGINS includes frontend URL
cat backend/.env | grep CORS

# Should include: ["http://localhost:3000"]
```

### Issue: Database connection error
```bash
# Check if postgres is running
docker-compose ps postgres

# If not running, start it
docker-compose up -d postgres

# Check migrations are applied
cd backend && alembic current
```

## 🎯 Admin Features at a Glance

| Feature | Route | Purpose |
|---------|-------|---------|
| Dashboard | `/admin/dashboard` | System overview |
| Users | `/admin/users` | All registered users |
| Pending | `/admin/pending-registrations` | New signups |
| Subscriptions | `/admin/subscriptions` | Approve access |
| Connected | `/admin/connected-users` | Active brokers |
| Strategies | `/admin/strategies` | Trading algorithms |
| Logs | `/admin/logs` | Execution history |
| Announcements | `/admin/announcements` | Platform messages |

## 🔒 Security Checklist

- [x] JWT tokens verified at middleware level
- [x] Super Admin role enforced on backend
- [x] HttpOnly cookies prevent XSS
- [x] CORS configured for known origins
- [x] Passwords hashed with pwdlib
- [x] Session expiry after 8 hours
- [x] Double verification (frontend + backend)

## 📱 Browser Support

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ⚠️  Requires JavaScript enabled
- ⚠️  Requires cookies enabled

## 🌐 Environment Variables Reference

### Frontend (`.env.local`)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000  # Backend API URL
JWT_SECRET_KEY=<secret>                          # Must match backend
```

### Backend (`backend/.env`)
```env
DATABASE_URL=postgresql+psycopg://stratum:stratum@localhost:5432/stratum
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<secret>                          # Must match frontend
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=480                          # 8 hours
COOKIE_SECURE=false                              # true for production
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMe123!
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

## 📞 Need More Help?

See the comprehensive guide: **ADMIN_ACCESS_GUIDE.md**

---

**Quick Reference** | Last Updated: July 20, 2026
