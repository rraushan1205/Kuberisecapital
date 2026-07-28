# Stratum Trading Platform

> Algorithmic trading platform with admin panel and user dashboard

## 🚀 Quick Start for Contributors

**New to the project? Get set up in 3 commands:**

```bash
# 1. Clone the repository
git clone https://github.com/rraushan1205/stratum.git
cd stratum

# 2. Run automated setup (installs everything)
chmod +x setup-dev.sh
./setup-dev.sh

# 3. Start development servers
./start-dev.sh
```

**That's it!** Open http://localhost:3000 and you're ready to develop.

**Admin Login:**
- URL: http://localhost:3000/admin/login
- Email: `admin@example.com`
- Password: `ChangeMe123!`

📖 **Detailed Setup Instructions:** See [SETUP_GUIDE.md](./SETUP_GUIDE.md)

---

## 🔒 Authentication Security Fix

### What Was Broken
Your login and signup had **ZERO security validation**:
- ❌ No password verification - forms just set a cookie without checking credentials
- ❌ No backend API calls - everything bypassed the server
- ❌ No JWT token validation - anyone could access dashboard
- ❌ Middleware only checked cookie existence (easily faked)

### What's Fixed Now
✅ **Real authentication** - Backend validates credentials with password hashing  
✅ **JWT tokens** - Proper token generation and validation  
✅ **Protected routes** - Middleware validates tokens on every request  
✅ **Account approval workflow** - Only APPROVED users can log in  
✅ **Secure sessions** - Tokens stored in HTTP cookies with proper expiration  

---

## 🚀 Quick Setup

### Step 1: Generate JWT Secret Key
```bash
openssl rand -base64 32
```
Copy the output (example: `xK8J9mP2nQ5rS7tV1wX3yZ6aC4bD8eF0gH2iJ4kL6...`)

### Step 2: Create Environment Files

**Frontend (.env.local):**
```bash
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
JWT_SECRET_KEY=PASTE_YOUR_SECRET_HERE
EOF
```

**Backend (backend/.env):**
```bash
cat > backend/.env << 'EOF'
DATABASE_URL=postgresql+psycopg://stratum:stratum@localhost:5432/stratum
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=PASTE_YOUR_SECRET_HERE
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=480
COOKIE_SECURE=false
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=AdminPass123!
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
STRATEGY_STORAGE_PATH=./storage/strategies
TRADING_ENGINE_URL=
EOF
```

**⚠️ CRITICAL:** Use the **EXACT SAME** JWT_SECRET_KEY in both files!

### Step 3: Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```
Backend runs at `http://localhost:8000`

### Step 4: Start Frontend
```bash
npm run dev
```
Frontend runs at `http://localhost:3000`

---

## 🧪 Test Authentication Works

### Test 1: Dashboard Protection
1. Open browser in incognito mode
2. Go to `http://localhost:3000/dashboard`
3. ✅ Should redirect to login (access denied)

### Test 2: Register New User
1. Go to `http://localhost:3000/register`
2. Fill form:
   - Full Name: `Test User`
   - Email: `test@example.com`
   - Phone: `1234567890`
   - Invitation Code: `VALID123`
   - Password: `SecurePass123!`
3. ✅ Should redirect to "pending approval" page

### Test 3: Login Blocked (Pending)
1. Go to `http://localhost:3000/login`
2. Email: `test@example.com`
3. Password: `SecurePass123!`
4. ✅ Should show: "Your account is pending approval"

### Test 4: Approve User
1. Go to `http://localhost:3000/admin/login`
2. Login with admin credentials (from backend/.env)
3. Go to "Pending Registrations"
4. Approve `test@example.com`

### Test 5: Login Success
1. Go to `http://localhost:3000/login`
2. Email: `test@example.com`
3. Password: `SecurePass123!`
4. ✅ Should login and show dashboard

### Test 6: Wrong Password Blocked
1. Clear cookies/use incognito
2. Try login with wrong password
3. ✅ Should show: "Invalid email or password"
4. Dashboard should NOT be accessible

---

## 📝 How Authentication Works

### Registration Flow:
1. User submits registration form
2. Frontend validates invitation code (mock check - replace with real API)
3. Frontend calls `POST /api/v1/auth/register`
4. Backend creates user with **PENDING** status
5. User redirected to pending approval page
6. Admin must approve before user can log in

### Login Flow:
1. User submits login form
2. Frontend calls `POST /api/v1/auth/login`
3. Backend validates:
   - User exists in database
   - Password matches hash
   - Account status is **APPROVED**
4. Backend generates JWT token (user ID + role)
5. Frontend stores JWT in cookie
6. User redirected to dashboard
7. Middleware validates JWT on every route

### Account Statuses:
- **PENDING** - Cannot log in, waiting for admin approval
- **REJECTED** - Cannot log in, account denied
- **APPROVED** - Can log in and access dashboard

---

## 🔐 Security Features

### Password Security:
- Hashed using `pwdlib` (industry-standard algorithm)
- Never stored in plain text
- Verification happens server-side only

### JWT Token Security:
- Signed with HS256 algorithm
- Contains user ID and role
- Expires after 8 hours (configurable)
- Validated on every protected route
- "Remember me" extends to 7 days

### Route Protection:
- Dashboard routes require valid JWT token
- Admin routes require SUPER_ADMIN role
- Invalid/expired tokens redirect to login
- No bypass possible - validation in middleware

---

## 📚 API Endpoints

### POST `/api/v1/auth/register`
Create new user account (PENDING status).

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response (201):**
```json
{
  "message": "Registration successful! Your account is pending admin approval.",
  "email": "user@example.com"
}
```

### POST `/api/v1/auth/login`
Authenticate and get JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "USER",
    "account_status": "APPROVED",
    "email_verified": false
  }
}
```

**Error Responses:**
- 401: Invalid credentials
- 403: Account pending/rejected

### GET `/api/v1/auth/account-status/{email}`
Check account status.

**Response (200):**
```json
{
  "email": "user@example.com",
  "account_status": "PENDING",
  "message": "Your account is pending approval."
}
```

### GET `/api/v1/client/dashboard`
Get dashboard data for authenticated user (requires valid JWT token).

**Headers:**
```
Cookie: stratum_token=<jwt_token>
```

**Response (200):**
```json
{
  "profile": {
    "name": "John Doe",
    "email": "user@example.com",
    "subscriptionStatus": "INACTIVE",
    "connectedBroker": null
  }
}
```

**Error Responses:**
- 401: Not authenticated or invalid token

### GET `/api/v1/client/marketplace/strategies`
Get available strategies in marketplace (requires authentication).

**Response (200):**
```json
[]
```

---

## 🐛 Troubleshooting

### "Failed to fetch" or "CORS error" in browser
**Fix:** Backend is not running or CORS settings incorrect

1. Make sure backend is running:
```bash
cd backend
python -m uvicorn app.main:app --reload
```

2. Check backend/.env has correct CORS settings:
```bash
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

3. Restart backend after changes.

**Note:** Admin logout will still work even if backend is offline (clears cookies locally).

### "403 Forbidden" on dashboard
**Fix:** JWT secrets don't match
```bash
# Check both files have SAME key:
cat .env.local | grep JWT_SECRET_KEY
cat backend/.env | grep JWT_SECRET_KEY
```
Restart both servers after fixing.

### "Invalid credentials" but password is correct
**Fix:** Check backend logs for errors
```bash
# Backend terminal shows detailed errors
# Or: tail -f backend.log
```
Verify user exists in database with APPROVED status.

### Registration fails
**Fix:** Database migration needed
```bash
cd backend
alembic upgrade head
```

### Middleware redirects with valid token
**Fix:** JWT_SECRET_KEY not loaded in Next.js
```bash
# Make sure .env.local exists in root
# Restart frontend: npm run dev
```

---

## 🔄 Files Modified

### Backend:
- `backend/app/schemas/auth.py` - Added login/register schemas
- `backend/app/api/auth.py` - Added login, register, account-status endpoints
- `backend/app/core/security.py` - Already had password/JWT functions

### Frontend:
- `src/lib/auth-client.ts` - Complete rewrite with real API calls
- `src/components/login-form.tsx` - Now calls backend login API
- `src/components/register-form.tsx` - Now calls backend register API
- `src/middleware.ts` - Now validates JWT tokens instead of cookie presence

---

## 🎯 Admin Panel

### Create First Admin (if needed)
```bash
cd backend
# Admin is auto-created on startup from .env
# Or manually via admin bootstrap script
```

### Admin Login
1. Go to `http://localhost:3000/admin/login`
2. Use credentials from backend/.env:
   - Email: `ADMIN_EMAIL`
   - Password: `ADMIN_PASSWORD`

### Admin Features
- **Pending Registrations** - Approve/reject user accounts
- **Users** - View all registered users
- **Connected Users** - See active sessions
- **Strategies** - Manage trading strategies
- **Execution Logs** - View system activity
- **Announcements** - Broadcast messages

---

## ✅ Production Checklist

Before deploying to production:

- [ ] Change JWT_SECRET_KEY to strong random value
- [ ] Change ADMIN_PASSWORD to secure password
- [ ] Set `COOKIE_SECURE=true` in backend/.env
- [ ] Enable HTTPS for secure cookie transmission
- [ ] Update CORS origins to production domains
- [ ] Update NEXT_PUBLIC_API_BASE_URL to production backend
- [ ] Set up proper database backups
- [ ] Configure rate limiting for auth endpoints
- [ ] Add email verification for registrations
- [ ] Replace mock invitation validation with real API
- [ ] Set up monitoring and alerting
- [ ] Review and test all security measures

---

## 🎉 Success Checklist

Your authentication is working when:

- [x] Dashboard redirects to login when not authenticated
- [x] Can register new users
- [x] Pending users cannot log in
- [x] Admin can approve users
- [x] Approved users can log in successfully
- [x] Wrong passwords are rejected
- [x] JWT tokens are validated on protected routes
- [x] Sessions expire after configured time
- [x] Direct dashboard URL access blocked without auth

**All checks passed? You're secured! 🔒**

---

## 📞 Support

For issues:
1. Check troubleshooting section above
2. Review backend logs
3. Check browser console for errors
4. Verify environment variables are correct
5. Ensure database is running and migrated

The authentication system now follows industry security best practices!
