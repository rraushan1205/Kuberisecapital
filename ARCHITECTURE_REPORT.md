# Stratum Platform - Architecture Report

**Generated:** 2026-07-23  
**Purpose:** Comprehensive architecture analysis before broker integration implementation

---

## 1. Project Overview

### Tech Stack

**Backend:**
- **Framework:** FastAPI 0.116.1
- **Language:** Python 3.11+
- **ORM:** SQLAlchemy 2.0.43
- **Database:** PostgreSQL (psycopg 3.2.10)
- **Cache/Sessions:** Redis 6.4.0
- **Migrations:** Alembic 1.16.5
- **Server:** Uvicorn 0.35.0 with uvloop
- **Authentication:** PyJWT 2.10.1
- **Password Hashing:** pwdlib with Argon2
- **HTTP Client:** httpx 0.28.1
- **Validation:** Pydantic 2.x with email-validator

**Frontend:**
- **Framework:** Next.js 15.3.2 (App Router)
- **Language:** TypeScript 5.8.3
- **React:** 19.1.0
- **Styling:** TailwindCSS 4.3.3
- **State Management:** Zustand 5.0.14
- **Data Fetching:** TanStack Query 5.101.2
- **Forms:** React Hook Form 7.58.1 with Zod validation
- **UI Components:** Radix UI primitives
- **Animations:** Framer Motion 12.9.2
- **Icons:** Lucide React 0.511.0
- **Theming:** next-themes 0.4.6
- **JWT:** jose 6.2.3

**Infrastructure:**
- **Database:** PostgreSQL
- **Cache:** Redis
- **Package Managers:** npm (frontend), pip + venv (backend)
- **Development:** Docker Compose (optional), shell scripts for local dev

### Project Type
Full-stack algorithmic trading platform with:
- Admin portal for user management and strategy oversight
- User dashboard for broker connections and strategy marketplace
- Account approval workflow (pending → approved/rejected)
- Strategy upload, start/stop controls
- Execution logging and announcements system

### Current Status
- ✅ Core authentication (admin + user sessions)
- ✅ Database schema with migrations
- ✅ Admin CRUD operations
- ✅ Role-based access control
- ✅ JWT cookie-based sessions
- ⚠️ Broker integration (database models exist, API endpoints missing)
- ⚠️ User-facing APIs (dashboard snapshot API referenced but not implemented)
- ⚠️ Email verification (UI ready, SMTP not configured)
- ⚠️ Trading engine integration (service layer exists, engine not implemented)

## 2. Directory Structure

```
stratum/
├── backend/                          # Python FastAPI backend
│   ├── alembic/                     # Database migrations
│   │   ├── versions/                # Migration scripts
│   │   │   └── 20260718_0001_initial_admin_schema.py
│   │   ├── env.py                   # Alembic environment config
│   │   └── script.py.mako           # Migration template
│   ├── app/
│   │   ├── api/                     # API route handlers
│   │   │   ├── admin.py            # Admin endpoints (COMPLETE)
│   │   │   └── dependencies.py      # FastAPI dependency injection
│   │   ├── core/                    # Core utilities
│   │   │   ├── config.py           # Pydantic settings
│   │   │   └── security.py         # JWT, password hashing
│   │   ├── db/                      # Database layer
│   │   │   ├── base.py             # SQLAlchemy Base
│   │   │   └── session.py          # Session factory
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   └── domain.py           # User, Strategy, BrokerConnection, etc.
│   │   ├── schemas/                 # Pydantic schemas (request/response)
│   │   │   └── admin.py            # Admin API schemas
│   │   ├── services/                # Business logic services
│   │   │   ├── admin_bootstrap.py  # Create initial super admin
│   │   │   └── trading_engine.py   # Trading engine HTTP client
│   │   └── main.py                  # FastAPI app entry point
│   ├── tests/
│   │   └── test_admin_auth.py      # Admin auth tests
│   ├── requirements.txt             # Python dependencies
│   ├── alembic.ini                  # Alembic config
│   ├── Dockerfile                   # Backend container
│   └── .env.example                 # Environment variables template
│
├── src/                             # Next.js frontend
│   ├── app/                         # App Router pages
│   │   ├── admin/                   # Admin portal routes
│   │   │   ├── (portal)/           # Protected admin routes (grouped)
│   │   │   │   ├── dashboard/
│   │   │   │   ├── users/
│   │   │   │   ├── pending-registrations/
│   │   │   │   ├── connected-users/
│   │   │   │   ├── strategies/
│   │   │   │   ├── logs/
│   │   │   │   ├── subscriptions/
│   │   │   │   ├── announcements/
│   │   │   │   └── layout.tsx      # Admin shell layout
│   │   │   └── login/
│   │   │       └── page.tsx         # Admin login
│   │   ├── dashboard/               # User dashboard routes
│   │   │   ├── broker/
│   │   │   ├── marketplace/
│   │   │   ├── settings/
│   │   │   ├── support/
│   │   │   ├── page.tsx             # Dashboard home
│   │   │   └── layout.tsx           # Dashboard shell
│   │   ├── login/
│   │   ├── register/
│   │   ├── forgot-password/
│   │   ├── reset-password/
│   │   ├── verify-email/
│   │   ├── pending-approval/
│   │   ├── account-rejected/
│   │   ├── layout.tsx               # Root layout
│   │   ├── page.tsx                 # Landing page
│   │   └── globals.css              # Global styles
│   ├── components/                  # Shared React components
│   │   ├── ui/                      # Base UI components
│   │   │   ├── button.tsx
│   │   │   ├── data-state.tsx       # Loading/error states
│   │   │   └── section-card.tsx
│   │   ├── auth-shell.tsx
│   │   ├── login-form.tsx
│   │   ├── register-form.tsx
│   │   └── theme-toggle.tsx
│   ├── features/                    # Feature modules (domain-driven)
│   │   ├── admin/                   # Admin feature module
│   │   │   ├── api/
│   │   │   │   └── admin-api.ts    # Admin API client
│   │   │   ├── components/          # Admin-specific components
│   │   │   ├── hooks/
│   │   │   │   └── use-admin-data.ts
│   │   │   ├── lib/
│   │   │   │   └── format.ts       # Formatting utilities
│   │   │   └── types.ts             # TypeScript types
│   │   └── dashboard/               # User dashboard feature
│   │       ├── api/
│   │       │   └── dashboard-api.ts
│   │       ├── components/
│   │       ├── hooks/
│   │       ├── store/
│   │       │   └── dashboard-ui-store.ts  # Zustand store
│   │       └── types.ts
│   ├── lib/                         # Shared utilities
│   │   ├── auth-client.ts          # Auth helpers (stub)
│   │   └── utils.ts                 # General utilities
│   ├── providers/
│   │   └── app-providers.tsx       # React Query + Theme providers
│   └── middleware.ts                # Next.js middleware (route protection)
│
├── .env.local.example               # Frontend env template
├── package.json                     # Node dependencies
├── tsconfig.json                    # TypeScript config
├── tailwind.config.ts               # Tailwind config
├── next.config.ts                   # Next.js config
├── docker-compose.yml               # PostgreSQL + Redis services
├── start-dev.sh                     # Development startup script
└── setup-dev.sh                     # Environment setup script
```

**Key Observations:**
- **Backend:** Well-organized layered architecture (routes → services → models)
- **Frontend:** Feature-based modules (`features/admin`, `features/dashboard`) with co-located API clients, components, hooks
- **Missing:** No `app/api/client.py` or user-facing API routes beyond admin
- **Missing:** No broker integration service modules yet

## 3. Backend Architecture

### Entry Point
**File:** `backend/app/main.py`

```python
app = FastAPI(title="Stratum API", version="1.0.0", lifespan=lifespan)
```

- **Lifespan:** Runs `ensure_initial_super_admin()` on startup
- **CORS:** Configured via `settings.backend_cors_origins`
- **Routers:** Only `admin_router` included (`/api/v1/admin/*`)

### Folder Organization

```
backend/app/
├── api/          # Route handlers (controllers)
├── core/         # Configuration, security, utilities
├── db/           # Database connection and session management
├── models/       # SQLAlchemy ORM models (domain entities)
├── schemas/      # Pydantic models (request/response DTOs)
└── services/     # Business logic services
```

### API Routing (`app/api/`)

**Current Files:**
- **`admin.py`** - Complete admin CRUD endpoints (login, users, strategies, logs, etc.)
- **`dependencies.py`** - FastAPI dependency injection for auth and DB session

**Pattern:**
```python
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.post("/auth/login")
def login_admin(payload: AdminLoginInput, response: Response, db: DbSession): ...
```

**Missing:**
- No `client.py` or user-facing API module
- No broker integration endpoints

### Services (`app/services/`)

**Existing:**
1. **`admin_bootstrap.py`**
   - `ensure_initial_super_admin(session)` - Creates super admin if none exists
   
2. **`trading_engine.py`**
   - `dispatch_engine_command(command, payload)` - HTTP client for external trading engine
   - Sends commands like `start`, `stop`, `force-square-off` to `TRADING_ENGINE_URL`

**Pattern:** Services are pure functions, not classes

### Models (`app/models/domain.py`)

All domain entities in single file:
- **User** - Core user model with roles, account status
- **BrokerConnection** - User ↔ Broker relationship (provider, status, connected_at)
- **Strategy** - Uploaded Python scripts
- **ExecutionLog** - Audit trail for strategy actions
- **Announcement** - Admin announcements

**Relationships:**
- User → BrokerConnection (1:M with cascade delete)
- User → Strategy (1:M via `uploaded_by_id`)
- Strategy → ExecutionLog (1:M nullable)

### Schemas (`app/schemas/`)

**Pattern:** Pydantic models with `BaseModel` (input) or `model_config = ConfigDict(from_attributes=True)` (output from ORM)

**Current:**
- `admin.py` - All admin-related schemas (login input, user output, strategy output, etc.)

**Missing:**
- No user/client schemas yet
- No broker-specific schemas

### Database Layer (`app/db/`)

**`session.py`:**
```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, ...)

def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

**`base.py`:**
```python
class Base(DeclarativeBase):
    pass
```

**Pattern:** Dependency injection via `DbSession = Annotated[Session, Depends(get_db)]`

### Authentication Flow (`app/core/security.py`)

**Password Hashing:**
```python
password_hash = PasswordHash.recommended()  # Argon2
hash_password(password) -> str
verify_password(password, hashed_password) -> bool
```

**JWT:**
```python
create_access_token(subject: str, role: str) -> str
decode_access_token(token: str) -> dict
```

- Payload: `{"sub": user_id, "role": role, "exp": timestamp}`
- Algorithm: HS256
- Expiry: 480 minutes (configurable)

### Dependency Injection (`app/api/dependencies.py`)

**Key Dependencies:**
```python
DbSession = Annotated[Session, Depends(get_db)]
SuperAdmin = Annotated[User, Depends(require_super_admin)]
```

**`require_super_admin()`:**
- Accepts JWT from `Authorization: Bearer <token>` OR `stratum_admin_session` cookie
- Validates JWT, extracts user ID
- Fetches user from DB, checks role == SUPER_ADMIN
- Returns User object or raises 401/403

### Middleware
**None explicitly defined** - FastAPI's default exception handling + CORS middleware

### Background Jobs
**None** - No Celery, no background task queue

## 4. Frontend Architecture

### App Router Structure

**Next.js 15 App Router** with route groups and layouts:

```
app/
├── admin/
│   ├── (portal)/          # Route group (doesn't affect URL)
│   │   ├── layout.tsx     # Admin shell (sidebar, header)
│   │   ├── dashboard/
│   │   ├── users/
│   │   └── ...
│   └── login/             # Public admin login
├── dashboard/             # User workspace
│   ├── layout.tsx         # Dashboard shell
│   ├── broker/
│   ├── marketplace/
│   └── ...
├── login/
├── register/
└── layout.tsx             # Root layout (providers, fonts)
```

**Route Groups:** `(portal)` creates shared layout without adding `/portal` to URL

### Layout Hierarchy

```
Root Layout (app/layout.tsx)
  └─ AppProviders (React Query + Theme)
      ├─ Admin Routes
      │   └─ Admin Shell Layout (admin/(portal)/layout.tsx)
      │       └─ Page components
      └─ User Routes
          └─ Dashboard Shell Layout (dashboard/layout.tsx)
              └─ Page components
```

### Components Organization

**Three-tier structure:**

1. **`src/components/`** - Shared primitives
   - `ui/` - Base components (button, data-state, section-card)
   - Auth components (login-form, register-form, auth-shell)

2. **`src/features/admin/components/`** - Admin-specific
   - Admin shell, login, dashboard, data tables, etc.
   - Co-located with admin feature

3. **`src/features/dashboard/components/`** - User dashboard
   - Broker page, marketplace, settings, etc.

**Pattern:** Feature modules own their components

### Context Providers (`src/providers/app-providers.tsx`)

```tsx
<ThemeProvider attribute="class" defaultTheme="system">
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
</ThemeProvider>
```

- **TanStack Query:** 30s stale time, 1 retry, no refetch on window focus
- **Next Themes:** System-aware dark mode

### State Management

**Two patterns:**

1. **Server State:** TanStack Query (React Query)
   - Used in `use-admin-data.ts` and `use-dashboard-data.ts`
   - Automatic caching, refetching, loading/error states

2. **UI State:** Zustand
   - `dashboard-ui-store.ts` - Client-side UI state (modals, filters, etc.)
   - Not used extensively yet

**No Redux, no Context for business state**

### API Client Organization

**Pattern:** Feature-based API clients

1. **`features/admin/api/admin-api.ts`**
   - `adminApi.login()`, `adminApi.getUsers()`, `adminApi.uploadStrategy()`, etc.
   - Custom `AdminApiError` class
   - Credentials: `include` (sends cookies)

2. **`features/dashboard/api/dashboard-api.ts`**
   - `getDashboardSnapshot()`, `getMarketplaceStrategies()`, `brokerConnectUrl()`
   - **These APIs don't exist in backend yet**

**Pattern:** Centralized fetch wrapper with error handling

### Middleware (`src/middleware.ts`)

**Route Protection Logic:**

```typescript
export async function middleware(request: NextRequest) {
  const hasSession = request.cookies.has("stratum_session");
  const adminSession = request.cookies.get("stratum_admin_session")?.value;
  const hasValidAdminSession = await hasValidSuperAdminSession(adminSession);
  
  // Admin routes: require valid admin JWT
  if (pathname.startsWith("/admin")) {
    if (pathname === "/admin/login") {
      if (hasValidAdminSession) redirect("/admin/dashboard");
      if (hasSession && !hasValidAdminSession) return forbidden();
    }
    if (!hasValidAdminSession) {
      if (hasSession || adminSession) return forbidden();
      redirect("/admin/login");
    }
  }
  
  // User dashboard: require session
  if (pathname.startsWith("/dashboard") && !hasSession) {
    redirect("/login?next=" + pathname);
  }
}
```

**JWT Verification:**
- Middleware verifies admin JWT using `jose` library
- Requires `JWT_SECRET_KEY` in `.env.local` (must match backend)
- Checks `role === "SUPER_ADMIN"` in payload

### Protected Routes

**Matcher:**
```typescript
export const config = {
  matcher: ["/dashboard/:path*", "/login", "/admin/:path*"],
};
```

**Protection Strategy:**
- Admin routes: JWT verification in middleware
- User routes: Cookie presence check (actual validation happens server-side)

## 5. Database

### Current Models

**1. User**
```sql
id              UUID PRIMARY KEY
email           VARCHAR(320) UNIQUE
password_hash   VARCHAR(512)
full_name       VARCHAR(160) NULL
role            ENUM(UserRole)
email_verified  BOOLEAN
account_status  ENUM(AccountStatus)
subscription_status ENUM(SubscriptionStatus)
created_at      TIMESTAMP
last_login_at   TIMESTAMP NULL
```

**2. BrokerConnection**
```sql
id            UUID PRIMARY KEY
user_id       UUID FK(users.id) ON DELETE CASCADE
provider      VARCHAR(64)
status        ENUM(BrokerStatus)
connected_at  TIMESTAMP NULL

UNIQUE(user_id, provider)
```

**3. Strategy**
```sql
id                  UUID PRIMARY KEY
name                VARCHAR(160) UNIQUE
script_filename     VARCHAR(260)
script_storage_key  VARCHAR(512) UNIQUE
status              ENUM(StrategyStatus)
uploaded_by_id      UUID FK(users.id) ON DELETE RESTRICT
created_at          TIMESTAMP
```

**4. ExecutionLog**
```sql
id              UUID PRIMARY KEY
action          ENUM(ExecutionAction)
message         TEXT
strategy_id     UUID FK(strategies.id) ON DELETE SET NULL (nullable)
initiated_by_id UUID FK(users.id) ON DELETE RESTRICT
created_at      TIMESTAMP

INDEX(action, created_at)
```

**5. Announcement**
```sql
id             UUID PRIMARY KEY
title          VARCHAR(160)
message        TEXT
created_by_id  UUID FK(users.id) ON DELETE RESTRICT
created_at     TIMESTAMP

INDEX(created_at)
```

### Relationships

```
User 1──M BrokerConnection (cascade delete)
User 1──M Strategy (restrict delete)
User 1──M ExecutionLog (restrict delete)
User 1──M Announcement (restrict delete)
Strategy 1──M ExecutionLog (set null on delete)
```

### Enums

**UserRole:**
- `USER` - Regular traders
- `ADMIN` - Admin users (not currently used)
- `SUPER_ADMIN` - Platform administrators

**AccountStatus:**
- `PENDING` - Awaiting admin approval
- `APPROVED` - Active account
- `REJECTED` - Account denied

**SubscriptionStatus:**
- `INACTIVE` - No active subscription
- `ACTIVE` - Subscription active

**BrokerStatus:**
- `DISCONNECTED` - Not connected
- `CONNECTED` - Active broker connection

**StrategyStatus:**
- `STOPPED` - Strategy not running
- `RUNNING` - Strategy executing

**ExecutionAction:**
- `STRATEGY_STARTED`
- `STRATEGY_STOPPED`
- `FORCE_SQUARE_OFF`

### Existing Migrations

**Single migration:** `20260718_0001_initial_admin_schema.py`

Creates all tables and enums. No incremental migrations yet.

**Migration Tool:** Alembic 1.16.5
- Config: `backend/alembic.ini`
- Env: `backend/alembic/env.py`
- Versions: `backend/alembic/versions/`

## 6. Authentication

### Complete Authentication Flow

#### Admin Login Flow

1. **User submits credentials** (`/admin/login`)
   ```
   POST /api/v1/admin/auth/login
   { email, password }
   ```

2. **Backend validates** (`backend/app/api/admin.py`)
   - Query user by email
   - Verify password with Argon2 hash
   - Check `role == SUPER_ADMIN`
   - Update `last_login_at`

3. **JWT generation** (`backend/app/core/security.py`)
   ```python
   token = create_access_token(str(user.id), user.role.value)
   # Payload: {"sub": user_id, "role": "SUPER_ADMIN", "exp": timestamp}
   ```

4. **Set HTTP-only cookie**
   ```python
   response.set_cookie(
       key="stratum_admin_session",
       value=token,
       httponly=True,
       secure=settings.cookie_secure,
       samesite="lax",
       max_age=28800,  # 8 hours
       path="/"
   )
   ```

5. **Frontend receives session** → Redirects to `/admin/dashboard`

#### User Login Flow (Partially Implemented)

1. **User submits credentials** (`/login`)
   - Frontend: `src/app/login/page.tsx`
   - **Backend endpoint missing** - No `/api/v1/client/auth/login` yet

2. **Expected flow:**
   - Verify email + password
   - Check `account_status == APPROVED`
   - Check `email_verified == True`
   - Generate JWT with `role == USER`
   - Set `stratum_session` cookie

3. **Current workaround:**
   - `src/lib/auth-client.ts` has stub `establishSession()`
   - Sets dummy cookie for frontend testing

#### Registration Flow (Partially Implemented)

1. **User submits registration** (`/register`)
   - Frontend: `src/app/register/page.tsx`
   - **Backend endpoint missing** - No `/api/v1/client/auth/register`

2. **Expected flow:**
   - Create user with `account_status = PENDING`
   - Set `email_verified = False`
   - Send verification email
   - Redirect to `/pending-approval`

3. **Admin approval:**
   ```
   POST /api/v1/admin/subscriptions/{user_id}/approve
   ```
   - Sets `account_status = APPROVED`
   - Sets `subscription_status = ACTIVE`

#### JWT Structure

**Admin JWT:**
```json
{
  "sub": "uuid-of-user",
  "role": "SUPER_ADMIN",
  "exp": 1234567890
}
```

**User JWT (expected):**
```json
{
  "sub": "uuid-of-user",
  "role": "USER",
  "exp": 1234567890
}
```

#### Cookie Configuration

**Admin:** `stratum_admin_session`
- HttpOnly: Yes
- Secure: Configurable (`COOKIE_SECURE`)
- SameSite: Lax
- Path: `/`
- Max-Age: 480 minutes

**User:** `stratum_session` (not implemented)
- Expected same configuration

#### Middleware Protection

**Frontend** (`src/middleware.ts`):
- Verifies admin JWT client-side using `jose`
- Requires `JWT_SECRET_KEY` in frontend `.env.local`
- Checks role in JWT payload
- Returns 403 if invalid

**Backend:**
- Dependency injection via `SuperAdmin = Annotated[User, Depends(require_super_admin)]`
- Extracts JWT from cookie or Bearer token
- Validates signature, expiry
- Fetches user from database
- Checks role matches

#### Role-Based Authorization

**Current roles:**
- `SUPER_ADMIN` - Full admin access
- `ADMIN` - Defined but not used
- `USER` - Regular users (no endpoints yet)

**Access control:**
- Admin endpoints: `SuperAdmin` dependency
- User endpoints: Not implemented (would need `CurrentUser` dependency)

#### Session Management

**Logout:**
```
POST /api/v1/admin/auth/logout
```
- Deletes `stratum_admin_session` cookie

**Session check:**
```
GET /api/v1/admin/auth/session
```
- Returns current admin user info from JWT

**No refresh tokens** - Sessions expire after JWT expiry (8 hours default)

## 7. Current APIs

### Admin APIs (`/api/v1/admin/*`)

**Authentication:**
- `POST /auth/login` - Admin login (sets JWT cookie)
- `POST /auth/logout` - Admin logout (clears cookie)
- `GET /auth/session` - Get current admin session

**User Management:**
- `GET /users` - List all users (ordered by created_at desc)
- `GET /pending-registrations` - List pending users (ordered by created_at asc)
- `POST /subscriptions/{user_id}/approve` - Approve user account + activate subscription

**Broker Connections:**
- `GET /connected-users` - List users with active broker connections (join User + BrokerConnection)

**Strategy Management:**
- `GET /strategies` - List all strategies
- `POST /strategies` - Upload new strategy (multipart/form-data)
  - Accepts: Python files only (`.py`)
  - Max size: 1 MB
  - Max strategies: 3 total
  - Stores in `STRATEGY_STORAGE_PATH`
- `POST /strategies/{strategy_id}/start` - Start strategy execution
- `POST /strategies/{strategy_id}/stop` - Stop strategy execution
- `POST /force-square-off` - Emergency square off all positions

**Execution Logs:**
- `GET /logs` - Get last 200 execution logs (ordered by created_at desc)

**Announcements:**
- `GET /announcements` - List all announcements
- `POST /announcements` - Create announcement

### User/Client APIs (`/api/v1/client/*`)

**Status: NOT IMPLEMENTED**

**Referenced in frontend but missing:**
- `GET /dashboard` - Get dashboard snapshot (broker status, stats)
- `GET /marketplace/strategies` - List marketplace strategies
- `GET /brokers/{provider}/connect` - Initiate broker OAuth flow
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout
- `GET /auth/session` - Get current user session

### Response Format

**Success responses:**
```json
{
  "id": "uuid",
  "field": "value",
  ...
}
```

**Error responses:**
```json
{
  "detail": "Error message"
}
```

**HTTP status codes:**
- 200: Success
- 201: Created
- 204: No content
- 400: Bad request
- 401: Unauthorized
- 403: Forbidden
- 404: Not found
- 409: Conflict
- 413: Payload too large
- 422: Validation error
- 502: Bad gateway (trading engine error)
- 503: Service unavailable (trading engine not configured)

## 8. Existing Services

### 1. Admin Bootstrap Service

**File:** `backend/app/services/admin_bootstrap.py`

**Function:** `ensure_initial_super_admin(session: Session) -> User | None`

**Purpose:**
- Creates initial super admin if none exists
- Runs on application startup (lifespan event)

**Logic:**
1. Check if any SUPER_ADMIN exists
2. If yes, return None
3. Check if ADMIN_EMAIL already taken by non-admin
4. If yes, raise RuntimeError
5. Create new user:
   - Email from `settings.admin_email`
   - Password from `settings.admin_password`
   - Role: SUPER_ADMIN
   - Email verified: True
   - Account status: APPROVED
   - Subscription status: ACTIVE
6. Commit to database
7. Print credentials to console

**Pattern:** Pure function, not a class

### 2. Trading Engine Service

**File:** `backend/app/services/trading_engine.py`

**Function:** `async dispatch_engine_command(command: str, payload: dict) -> None`

**Purpose:**
- Send HTTP commands to external trading engine
- Used by strategy start/stop and force square-off endpoints

**Commands:**
- `start` - Start strategy execution
- `stop` - Stop strategy execution
- `force-square-off` - Emergency position closure

**Logic:**
1. Check if `TRADING_ENGINE_URL` configured
2. If not, raise 503 Service Unavailable
3. POST to `{TRADING_ENGINE_URL}/commands/{command}` with JSON payload
4. Timeout: 20 seconds
5. On httpx.HTTPError, raise 502 Bad Gateway

**Pattern:** Async function, uses httpx.AsyncClient

**Current status:** Service exists but trading engine not implemented

### Service Patterns

**Observations:**
- Services are **pure functions**, not classes
- No service layer abstraction/interface
- Business logic directly in route handlers or services
- No repository pattern
- No unit of work pattern

**Convention:**
- Services live in `app/services/`
- Named `{domain}_{purpose}.py`
- Import from routes: `from app.services.trading_engine import dispatch_engine_command`

## 9. Existing Integrations

### External Trading Engine

**Type:** HTTP API integration  
**Status:** ⚠️ Interface exists, implementation missing  
**Configuration:** `TRADING_ENGINE_URL` environment variable

**Integration point:** `backend/app/services/trading_engine.py`

**Expected API contract:**
```
POST {TRADING_ENGINE_URL}/commands/start
POST {TRADING_ENGINE_URL}/commands/stop
POST {TRADING_ENGINE_URL}/commands/force-square-off

Request body: { "strategy_id": "uuid", ... }
Response: Any (status code matters)
```

**Current behavior:**
- If `TRADING_ENGINE_URL` not set → 503 Service Unavailable
- If engine unreachable → 502 Bad Gateway

### Broker APIs

**Type:** OAuth/API integrations (planned)  
**Status:** ⚠️ Database models exist, no integration code  
**Providers referenced in frontend:** Fyers, Groww

**Database support:**
- `BrokerConnection` model with `provider` field
- `broker_status` enum (CONNECTED/DISCONNECTED)
- Unique constraint: (user_id, provider)

**Frontend placeholder:**
```typescript
function brokerConnectUrl(provider: "fyers" | "groww") {
  return `${apiBaseUrl}/api/v1/client/brokers/${provider}/connect`;
}
```

**Missing:**
- No broker service modules
- No OAuth callback handlers
- No broker API clients
- No credential storage (beyond database connection record)

### Email Service

**Type:** SMTP integration (planned)  
**Status:** ⚠️ UI flows exist, email sending not implemented

**Email flows needed:**
1. Email verification (registration)
2. Password reset
3. Admin notifications

**Frontend ready:**
- `/verify-email/success`
- `/verify-email/expired`
- `/reset-password`

**Backend missing:**
- No SMTP configuration
- No email templates
- No email service module

### Redis

**Type:** Cache/session store  
**Status:** ⚠️ Configured but not actively used  
**Configuration:** `REDIS_URL` environment variable

**Current usage:** None identified in codebase

**Potential uses:**
- Rate limiting
- Session storage (alternative to JWT-only)
- Caching database queries
- WebSocket connection state

### PostgreSQL

**Type:** Primary database  
**Status:** ✅ Fully operational  
**Configuration:** `DATABASE_URL` environment variable

**Connection:**
- SQLAlchemy engine with connection pooling
- `pool_pre_ping=True` for connection health checks

## 10. Configuration

### Backend Environment Variables

**File:** `backend/.env` (from `.env.example`)

```ini
# Database
DATABASE_URL=postgresql+psycopg://stratum:stratum@localhost:5432/stratum

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=replace-with-a-long-unique-secret
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=480

# Security
COOKIE_SECURE=false  # Set true in production (HTTPS)

# Admin Bootstrap
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMe123!

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]

# Storage
STRATEGY_STORAGE_PATH=./storage/strategies

# External Services
TRADING_ENGINE_URL=  # Optional, for trading engine integration
```

### Frontend Environment Variables

**File:** `.env.local` (from `.env.local.example`)

```ini
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# JWT Secret (must match backend)
JWT_SECRET_KEY=replace-with-a-long-unique-secret
```

### Settings Class

**File:** `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480
    cookie_secure: bool = True
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMe123!"
    backend_cors_origins: list[str] = []
    strategy_storage_path: Path = Path("./storage/strategies")
    trading_engine_url: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env", ...)
```

**Access:** `from app.core.config import get_settings`  
**Pattern:** LRU cached singleton via `@lru_cache`

### Secrets Management

**Current approach:**
- Plain text `.env` files (not committed to git)
- No encryption
- No secret rotation
- No external secret manager (AWS Secrets Manager, Vault, etc.)

**Production considerations:**
- JWT_SECRET_KEY should be cryptographically random (32+ bytes)
- ADMIN_PASSWORD should be changed immediately
- Database credentials should use strong passwords
- Consider environment-specific secrets (dev, staging, prod)

### Configuration Best Practices

**✅ Good:**
- Environment-based configuration
- Pydantic validation
- Type-safe settings
- Sensible defaults

**⚠️ Needs improvement:**
- No secret rotation mechanism
- Hardcoded admin credentials in env
- No configuration for multiple environments
- No vault integration

## 11. Project Conventions

### Naming Conventions

**Backend (Python):**
- **Files:** `snake_case.py` (e.g., `admin_bootstrap.py`)
- **Classes:** `PascalCase` (e.g., `AdminLoginInput`, `UserRole`)
- **Functions:** `snake_case` (e.g., `ensure_initial_super_admin`)
- **Variables:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `JWT_SECRET_KEY`)
- **Database tables:** `snake_case` (e.g., `broker_connections`)
- **Enums:** `PascalCase` class, `UPPER_CASE` values (e.g., `UserRole.SUPER_ADMIN`)

**Frontend (TypeScript):**
- **Files:** `kebab-case.tsx` (e.g., `admin-login-form.tsx`)
- **Components:** `PascalCase` (e.g., `AdminLoginForm`)
- **Functions:** `camelCase` (e.g., `getDashboardSnapshot`)
- **Variables:** `camelCase`
- **Types:** `PascalCase` (e.g., `AdminSession`)
- **Constants:** `UPPER_SNAKE_CASE` or `camelCase`

### Folder Conventions

**Backend:**
- `app/api/` - Route handlers (one file per domain)
- `app/models/` - ORM models (domain.py contains all entities)
- `app/schemas/` - Pydantic DTOs (one file per domain)
- `app/services/` - Business logic (pure functions)
- `app/core/` - Core utilities (config, security)
- `app/db/` - Database infrastructure

**Frontend:**
- `app/` - Next.js pages (route-based)
- `features/{domain}/` - Feature modules with:
  - `api/` - API client
  - `components/` - Feature-specific components
  - `hooks/` - Custom hooks
  - `types.ts` - TypeScript types
  - `store/` - Zustand stores (if needed)
- `components/` - Shared components
- `lib/` - Shared utilities

### Dependency Injection Pattern

**Backend:**
```python
# Define dependency
def get_db() -> Generator[Session, None, None]:
    ...

# Annotate for reuse
DbSession = Annotated[Session, Depends(get_db)]

# Use in route
@router.get("/users")
def list_users(db: DbSession) -> list[User]:
    ...
```

**Pattern:** FastAPI dependency injection with type annotations

### Error Handling

**Backend:**
```python
# HTTPException for API errors
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="User account was not found."
)
```

**Frontend:**
```typescript
// Custom error classes
class AdminApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

// Try-catch in API calls
try {
  const data = await fetch(...);
} catch (error) {
  throw new AdminApiError(message, status);
}
```

### Logging

**Backend:**
- Uses Uvicorn's default logging
- No custom logger configuration
- No structured logging
- Logs printed to stdout (captured by `start-dev.sh` to `backend.log`)

**Frontend:**
- No logging framework
- Console.log for debugging (should be removed in production)

**Missing:**
- Request ID tracking
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Log aggregation (ELK, Datadog, CloudWatch)
- Audit logging for sensitive operations

### Response Format

**Backend:**
- **Success:** Return Pydantic model or primitive (FastAPI serializes to JSON)
- **Error:** `{"detail": "Error message"}`
- **No envelope pattern** (no `{success: true, data: {...}}`)

**Frontend:**
- Receives JSON directly
- Type-safe with TypeScript interfaces

### Coding Style

**Backend:**
- Python type hints everywhere
- Pydantic for validation
- No docstrings (should be added)
- Short functions (mostly single responsibility)

**Frontend:**
- TypeScript strict mode
- Functional components (no class components)
- React hooks pattern
- Colocated styles (TailwindCSS inline classes)

## 12. Extensibility Analysis

### Best Place to Add Broker Integrations

#### Recommended Structure

```
backend/app/
├── api/
│   ├── admin.py
│   ├── client.py         # NEW: User-facing APIs
│   └── dependencies.py
├── services/
│   ├── brokers/          # NEW: Broker integrations
│   │   ├── __init__.py
│   │   ├── base.py       # Abstract broker interface
│   │   ├── zerodha.py    # Zerodha implementation
│   │   ├── fyers.py      # Fyers implementation
│   │   ├── groww.py      # Groww implementation
│   │   ├── dhan.py       # Dhan implementation
│   │   └── angel_one.py  # Angel One implementation
│   └── broker_manager.py # NEW: Broker factory/orchestration
└── schemas/
    └── broker.py         # NEW: Broker-specific schemas
```

### Why This Approach?

**1. Separation of Concerns:**
- Each broker gets its own module
- Base class defines common interface
- Easy to add new brokers without touching existing code

**2. Follows Existing Patterns:**
- Services are in `app/services/`
- Pure functions or classes
- No global state

**3. Scalable:**
- Each broker can have unique auth flow (OAuth2, API key, etc.)
- Provider-specific error handling
- Independent testing

### Base Broker Interface

```python
# backend/app/services/brokers/base.py
from abc import ABC, abstractmethod
from typing import Any

class BrokerProvider(ABC):
    """Abstract base for all broker integrations"""
    
    @abstractmethod
    def get_auth_url(self, user_id: str, redirect_uri: str) -> str:
        """Generate OAuth/login URL"""
        pass
    
    @abstractmethod
    async def handle_callback(self, code: str, state: str) -> dict[str, Any]:
        """Process OAuth callback"""
        pass
    
    @abstractmethod
    async def get_positions(self, user_id: str) -> list[dict]:
        """Fetch user positions"""
        pass
    
    @abstractmethod
    async def place_order(self, user_id: str, order: dict) -> dict:
        """Place trading order"""
        pass
    
    @abstractmethod
    async def get_account_info(self, user_id: str) -> dict:
        """Get account details"""
        pass
```

### Broker Manager (Factory Pattern)

```python
# backend/app/services/broker_manager.py
from app.services.brokers.base import BrokerProvider
from app.services.brokers import zerodha, fyers, groww, dhan, angel_one

BROKERS: dict[str, type[BrokerProvider]] = {
    "zerodha": zerodha.ZerodhaBroker,
    "fyers": fyers.FyersBroker,
    "groww": groww.GrowwBroker,
    "dhan": dhan.DhanBroker,
    "angelone": angel_one.AngelOneBroker,
}

def get_broker(provider: str) -> BrokerProvider:
    if provider not in BROKERS:
        raise ValueError(f"Unsupported broker: {provider}")
    return BROKERS[provider]()
```

### API Endpoints Structure

```python
# backend/app/api/client.py (NEW FILE)
from fastapi import APIRouter
from app.services.broker_manager import get_broker

router = APIRouter(prefix="/api/v1/client", tags=["client"])

@router.get("/brokers/{provider}/connect")
async def initiate_broker_connection(
    provider: str,
    current_user: CurrentUser,
    db: DbSession
):
    broker = get_broker(provider)
    auth_url = broker.get_auth_url(str(current_user.id), ...)
    return {"redirect_url": auth_url}

@router.get("/brokers/{provider}/callback")
async def broker_oauth_callback(
    provider: str,
    code: str,
    state: str,
    db: DbSession
):
    broker = get_broker(provider)
    result = await broker.handle_callback(code, state)
    # Update BrokerConnection in database
    # Set status = CONNECTED, connected_at = now()
    ...
```

### Current Architecture Assessment

**✅ Strengths:**
- Clean separation: API → Services → Models
- Database models already support broker connections
- Feature-based frontend structure ready for extension

**⚠️ Gaps:**
- No broker service layer yet
- No user authentication endpoints
- No credential encryption/storage strategy
- No webhook handlers for broker events

### Architectural Improvements Before Broker Integration

**1. Add User Authentication:**
- Create `app/api/client.py` with login/register/logout
- Add `CurrentUser` dependency (like `SuperAdmin`)
- Implement user session management

**2. Credential Storage:**
- Add encrypted credential storage
- Options:
  - Database column with encryption at rest
  - External secret store (AWS Secrets Manager, Vault)
  - Hybrid: store encrypted tokens in DB, keys in secret manager

**3. Token Refresh:**
- Most broker OAuth tokens expire (24 hours typical)
- Need background job to refresh tokens
- Consider Celery or APScheduler

**4. Webhook Support:**
- Brokers send webhooks for order updates, position changes
- Need public endpoints: `/api/v1/webhooks/{provider}`
- Verify webhook signatures

**5. Rate Limiting:**
- Broker APIs have rate limits
- Implement rate limiting (Redis-backed)
- Queue requests if needed

**6. Logging & Monitoring:**
- Log all broker API calls
- Track success/failure rates
- Alert on credential expiry

## 13. Risks

### 1. Security Risks

**Credential Storage:**
- **Risk:** Broker access tokens stored in plain text
- **Impact:** HIGH - Full account access if database compromised
- **Mitigation:** Encrypt tokens at rest, use secret manager, implement token rotation

**JWT Secret Exposed:**
- **Risk:** Frontend needs JWT_SECRET_KEY for middleware verification
- **Impact:** MEDIUM - If leaked, attackers can forge admin sessions
- **Mitigation:** Move JWT verification to backend, use frontend middleware only for routing

**No Rate Limiting:**
- **Risk:** API abuse, brute force attacks
- **Impact:** MEDIUM - Service degradation, account lockouts
- **Mitigation:** Implement rate limiting on login, sensitive endpoints

### 2. Data Integrity Risks

**No Transaction Boundaries:**
- **Risk:** Database operations not wrapped in transactions
- **Impact:** MEDIUM - Partial updates on failure
- **Mitigation:** Use SQLAlchemy session.begin() for multi-step operations

**Cascade Deletes:**
- **Risk:** Deleting user cascades to BrokerConnections
- **Impact:** LOW - Acceptable for this use case, but be aware
- **Mitigation:** Document cascade behavior, add soft deletes if needed

### 3. Scalability Risks

**No Caching:**
- **Risk:** Database queries on every request
- **Impact:** MEDIUM - Slow response times at scale
- **Mitigation:** Use Redis for caching, implement cache invalidation strategy

**Synchronous Broker Calls:**
- **Risk:** Broker API calls block request thread
- **Impact:** HIGH - Slow or unavailable broker = slow application
- **Mitigation:** Use async/await properly, implement timeouts, add circuit breaker

**Single Database Connection Pool:**
- **Risk:** Connection exhaustion under load
- **Impact:** HIGH - Application becomes unresponsive
- **Mitigation:** Configure pool size appropriately, monitor connections

### 4. Integration Risks

**No Broker API Mocks:**
- **Risk:** Testing requires real broker accounts
- **Impact:** MEDIUM - Slow tests, can't test error scenarios
- **Mitigation:** Create broker API mocks for testing

**Trading Engine Dependency:**
- **Risk:** Trading engine not implemented, URL configuration unclear
- **Impact:** HIGH - Strategy execution won't work
- **Mitigation:** Define clear interface, create stub implementation, document deployment

**No Webhook Verification:**
- **Risk:** Fake webhook calls from attackers
- **Impact:** HIGH - Unauthorized trading actions
- **Mitigation:** Verify webhook signatures, use HMAC validation

### 5. Operational Risks

**No Monitoring:**
- **Risk:** No visibility into errors, performance
- **Impact:** HIGH - Can't detect outages, slow response to issues
- **Mitigation:** Add structured logging, APM (Datadog, New Relic), error tracking (Sentry)

**No Backup Strategy:**
- **Risk:** Database loss = complete data loss
- **Impact:** CRITICAL - Unrecoverable
- **Mitigation:** Automated PostgreSQL backups, test restore procedures

**No Health Checks:**
- **Risk:** Can't detect partial outages (DB up, Redis down)
- **Impact:** MEDIUM - False positives in monitoring
- **Mitigation:** Add comprehensive health check endpoint

### 6. Compliance Risks

**No Audit Logging:**
- **Risk:** Can't track who did what, when
- **Impact:** HIGH - Regulatory compliance issues, can't investigate incidents
- **Mitigation:** Add audit log table, log all sensitive operations

**No Data Retention Policy:**
- **Risk:** Indefinite data storage
- **Impact:** MEDIUM - GDPR, data minimization issues
- **Mitigation:** Define retention periods, implement data purging

### 7. Technical Debt

**No Tests:**
- **Risk:** Changes break existing functionality
- **Impact:** HIGH - Unstable platform
- **Mitigation:** Add unit tests, integration tests, CI/CD pipeline

**Hardcoded Limits:**
- **Risk:** Max 3 strategies hardcoded in code
- **Impact:** LOW - Inflexible, requires code changes
- **Mitigation:** Move to configuration or database

**No API Versioning:**
- **Risk:** Breaking changes affect clients
- **Impact:** MEDIUM - Frontend breaks on backend updates
- **Mitigation:** Version APIs (`/api/v1/`, `/api/v2/`)

## 14. Final Recommendation

### Broker Integration Implementation Strategy

Based on the comprehensive architecture analysis, here's the recommended approach for implementing broker integrations:

---

### ✅ Immediate Prerequisites (Must Complete First)

**1. Implement User Authentication APIs**
- Create `/api/v1/client/auth/login`, `register`, `logout`
- Add `CurrentUser` dependency injection
- User endpoints are referenced by frontend but don't exist

**2. Secure Credential Storage**
- Add encryption for broker access tokens
- Options:
  - **Simple:** AES-256 encryption in database with key in environment
  - **Better:** AWS Secrets Manager or HashiCorp Vault
  - **Best:** Hybrid approach (encrypted in DB, keys rotated via secret manager)

**3. Move JWT Verification to Backend**
- Remove `JWT_SECRET_KEY` from frontend `.env.local`
- Frontend middleware should only check cookie presence
- Backend validates JWT on every protected request
- **Security fix for exposed JWT secret**

---

### 🏗️ Broker Integration Architecture

**Use the Service Layer Pattern:**

```
app/services/brokers/
├── __init__.py
├── base.py              # BrokerProvider abstract class
├── zerodha.py           # from fyers import Zerodha
├── fyers.py             # from fyers import Fyers  
├── groww.py             # Custom implementation
├── dhan.py              # from dhanhq import dhanhq
└── angel_one.py         # from smartapi.smartConnect import SmartConnect
```

**Each broker module implements:**
```python
class BrokerProvider(ABC):
    @abstractmethod
    def get_auth_url(user_id, redirect_uri) -> str
    
    @abstractmethod
    async def handle_callback(code, state) -> dict
    
    @abstractmethod
    async def get_positions(user_id) -> list
    
    @abstractmethod
    async def place_order(user_id, order) -> dict
    
    @abstractmethod
    async def refresh_token(user_id) -> None
```

**Broker Manager (Factory):**
```python
# app/services/broker_manager.py
def get_broker(provider: str) -> BrokerProvider:
    return BROKERS[provider]()  # Factory pattern
```

---

### 📋 Implementation Phases

**Phase 1: Foundation (Week 1)**
1. ✅ Create `app/api/client.py` with user auth endpoints
2. ✅ Add `CurrentUser` dependency
3. ✅ Implement credential encryption
4. ✅ Add broker base interface (`app/services/brokers/base.py`)
5. ✅ Create broker factory (`app/services/broker_manager.py`)

**Phase 2: First Broker Integration (Week 2)**
1. ✅ Implement Zerodha broker (most popular in India)
2. ✅ Add OAuth flow: `/client/brokers/zerodha/connect`
3. ✅ Add callback handler: `/client/brokers/zerodha/callback`
4. ✅ Store encrypted access token in `BrokerConnection`
5. ✅ Test complete connection flow

**Phase 3: Additional Brokers (Week 3-4)**
1. ✅ Add Fyers, Groww, Dhan, Angel One following same pattern
2. ✅ Each takes 1-2 days (OAuth flow + API client)
3. ✅ Reuse existing `BrokerConnection` model (provider field)

**Phase 4: Token Management (Week 5)**
1. ✅ Background job for token refresh (Celery or APScheduler)
2. ✅ Handle token expiry gracefully
3. ✅ Notify users of disconnections

**Phase 5: Trading Operations (Week 6)**
1. ✅ Implement `get_positions()` for all brokers
2. ✅ Implement `place_order()` for all brokers
3. ✅ Add order status tracking

**Phase 6: Webhooks & Events (Week 7)**
1. ✅ Add webhook endpoints `/api/v1/webhooks/{provider}`
2. ✅ Verify webhook signatures
3. ✅ Process order updates, position changes

---

### 🎯 Why This Approach?

**1. Minimal Code Changes Per Broker**
- Abstract interface defined once
- Each new broker = single Python file
- No changes to database schema
- No changes to frontend (provider names already hardcoded)

**2. Follows Existing Conventions**
- Services in `app/services/`
- Pure functions/classes pattern
- FastAPI dependency injection
- Pydantic validation

**3. Testable & Maintainable**
- Mock `BrokerProvider` for tests
- Each broker independently testable
- Easy to add new brokers (just implement interface)

**4. Scalable**
- Factory pattern allows runtime broker selection
- Async/await for non-blocking broker calls
- Can add caching at broker layer
- Circuit breaker pattern can wrap each broker

---

### ⚠️ Critical Success Factors

**1. Don't store credentials in plain text** - Use encryption from day 1

**2. Implement proper error handling** - Broker APIs fail often (network, rate limits, maintenance)

**3. Add comprehensive logging** - Log every broker API call for debugging

**4. Test with real broker accounts** - Sandboxes don't always match production

**5. Handle token expiry gracefully** - Most tokens expire after 24 hours

**6. Implement rate limiting** - Protect against abuse and broker API limits

**7. Document broker setup** - Each broker requires app registration, API keys

---

### 📊 Estimated Effort

- **User auth APIs:** 2-3 days
- **Credential encryption:** 1-2 days  
- **Base broker interface:** 1 day
- **First broker (Zerodha):** 3-5 days
- **Additional brokers:** 2-3 days each
- **Token management:** 3-4 days
- **Webhooks:** 2-3 days

**Total: 4-6 weeks for full broker integration**

---

### ✨ Final Recommendation

The Stratum platform has a **solid foundation** with well-organized backend/frontend separation, clean database schema, and feature-based architecture. The broker integration should follow the **service layer pattern** with:

1. Abstract `BrokerProvider` interface
2. One service module per broker
3. Factory pattern for broker selection
4. Encrypted credential storage
5. Background token refresh
6. Comprehensive error handling

**Start with Zerodha** (largest user base in India), validate the pattern, then add other brokers incrementally. The existing `BrokerConnection` model already supports multiple providers, so no schema changes needed.

**Address security risks first** (credential encryption, JWT secret removal from frontend) before implementing broker integrations.

---

**End of Architecture Report**
