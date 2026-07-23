# Stratum Platform - Broker Implementation Analysis

**Generated:** 2026-07-23  
**Purpose:** Detailed analysis of existing broker-related code before implementation

---

## 1. Existing Broker Models

### BrokerConnection Model

**Location:** `backend/app/models/domain.py` (lines 61-72)

```python
class BrokerConnection(Base):
    __tablename__ = "broker_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_broker_connection_user_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[BrokerStatus] = mapped_column(Enum(BrokerStatus, name="broker_status"), default=BrokerStatus.DISCONNECTED)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="broker_connections")
```

### Broker-Related Enums

**Location:** `backend/app/models/domain.py` (lines 28-31)

```python
class BrokerStatus(str, enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
```

### Database Schema

**Fields in `broker_connections` table:**
- `id` (UUID, PK) - Unique connection identifier
- `user_id` (UUID, FK → users.id, CASCADE DELETE, INDEXED) - Owner of the connection
- `provider` (VARCHAR(64)) - Broker name (e.g., "zerodha", "fyers", "groww")
- `status` (ENUM: BrokerStatus) - Connection state (CONNECTED/DISCONNECTED)
- `connected_at` (TIMESTAMP, nullable) - When connection was established

**Constraints:**
- UNIQUE(user_id, provider) - One user cannot have duplicate connections to same broker
- Foreign key cascade: Deleting user → deletes all broker connections

### Relationship to User Model

**User Model** (lines 44-59):
```python
class User(Base):
    # ... other fields ...
    broker_connections: Mapped[list["BrokerConnection"]] = relationship(
        back_populates="user", 
        cascade="all, delete-orphan"
    )
```

**Usage pattern:**
- One-to-Many: User → BrokerConnection
- Cascade delete: User deletion removes all broker connections
- Bidirectional relationship via `back_populates`

### How BrokerConnection is Currently Used

**Admin Dashboard** (`backend/app/api/admin.py`, lines 99-117):
```python
@router.get("/connected-users", response_model=list[ConnectedUserOutput])
def list_connected_users(_: SuperAdmin, db: DbSession) -> list[ConnectedUserOutput]:
    statement = (
        select(BrokerConnection, User)
        .join(User, BrokerConnection.user_id == User.id)
        .where(BrokerConnection.status == BrokerStatus.CONNECTED)
        .order_by(BrokerConnection.connected_at.desc())
    )
    return [
        ConnectedUserOutput(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            provider=connection.provider,
            status=connection.status,
            connected_at=connection.connected_at,
        )
        for connection, user in db.execute(statement).all()
    ]
```

**Admin Schema** (`backend/app/schemas/admin.py`, lines 33-40):
```python
class ConnectedUserOutput(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str | None
    provider: str
    status: BrokerStatus
    connected_at: datetime | None
```

### Current Limitations

**What's missing:**
- ❌ No OAuth token storage (access_token, refresh_token)
- ❌ No token expiry tracking
- ❌ No broker-specific metadata (api_key, app_id, etc.)
- ❌ No credential encryption
- ❌ No last_sync_at timestamp
- ❌ No error/failure tracking

**What exists:**
- ✅ Basic connection status tracking
- ✅ Provider identification
- ✅ User relationship with cascade delete
- ✅ Unique constraint preventing duplicate connections
- ✅ Admin visibility into connected users

## 2. Current Dashboard Broker Flow

### Frontend Components

**Main Broker Page** (`src/features/dashboard/components/broker-page.tsx`):

```typescript
// Lines 10-13: Hardcoded providers
const providers = [
  { id: "fyers" as const, name: "Fyers" },
  { id: "groww" as const, name: "Groww" },
];

// Lines 15-19: Data fetching
export function BrokerPage() {
  const { data, isLoading, isError } = useDashboardSnapshot();
  const connectedProvider = data?.broker?.provider?.toLowerCase();
  const connectionStatus = data?.broker?.status;
  // ... renders provider cards ...
}
```

**Key observations:**
- Only 2 providers shown: Fyers, Groww
- Data comes from `useDashboardSnapshot()` hook
- Checks `data?.broker?.provider` and `data?.broker?.status`
- Connect button links to `brokerConnectUrl(provider.id)`

### API Layer

**Dashboard API Client** (`src/features/dashboard/api/dashboard-api.ts`):

```typescript
// Lines 21-23: Dashboard snapshot (NOT IMPLEMENTED)
export function getDashboardSnapshot() {
  return getJson<DashboardSnapshot>("/api/v1/client/dashboard");
}

// Lines 29-31: Broker connect URL generator
export function brokerConnectUrl(provider: "fyers" | "groww") {
  return `${apiBaseUrl}/api/v1/client/brokers/${provider}/connect`;
}
```

**Dashboard Types** (`src/features/dashboard/types.ts`):

```typescript
// Lines 1: Supported brokers
export type BrokerProvider = "fyers" | "groww";

// Lines 3-33: Expected dashboard response
export type DashboardSnapshot = {
  broker?: {
    provider?: string | null;
    status?: string | null;
  } | null;
  // ... other fields ...
};
```

### Data Fetching Hook

**React Query Hook** (`src/features/dashboard/hooks/use-dashboard-data.ts`):

```typescript
export function useDashboardSnapshot() {
  return useQuery({ 
    queryKey: ["dashboard", "snapshot"], 
    queryFn: getDashboardSnapshot 
  });
}
```

### Backend Status

**❌ MISSING ENDPOINTS:**

None of these exist in `backend/app/api/`:

1. `GET /api/v1/client/dashboard` - Dashboard snapshot
2. `GET /api/v1/client/brokers/{provider}/connect` - Initiate OAuth
3. `GET /api/v1/client/brokers/{provider}/callback` - OAuth callback
4. Any other client-facing endpoints

**✅ EXISTING ENDPOINT:**

Only admin endpoint exists:
```python
GET /api/v1/admin/connected-users  # Lists all users with active broker connections
```

### Current Flow Visualization

```
User Dashboard (broker-page.tsx)
    ↓
useDashboardSnapshot() hook
    ↓
getDashboardSnapshot() API call
    ↓
GET /api/v1/client/dashboard ❌ (404 - Not implemented)
    ↓
Frontend shows loading/error state
```

**Connect flow:**
```
User clicks "Connect Fyers"
    ↓
Opens URL: /api/v1/client/brokers/fyers/connect ❌ (404)
    ↓
Expected: Redirect to Fyers OAuth
Actual: Error
```

### What Frontend Expects

Based on the TypeScript types, the backend should return:

```json
{
  "broker": {
    "provider": "fyers",
    "status": "CONNECTED"
  },
  "profile": { "name": "John Doe", "subscriptionStatus": "ACTIVE" },
  "strategy": { "status": "RUNNING", "selectedName": "Strategy 1" },
  "pnl": { "daily": "₹1,250", "overall": "₹45,000" },
  "positions": { "open": 3, "closed": 12 },
  "subscription": { "status": "ACTIVE" },
  "preferences": { "lotSize": "1", "riskSettings": "Medium" }
}
```

## 3. Authentication Context

### Current Admin Authentication

**Dependency:** `SuperAdmin = Annotated[User, Depends(require_super_admin)]`

**Implementation** (`backend/app/api/dependencies.py`, lines 17-37):

```python
def require_super_admin(
    db: DbSession,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    admin_session: Annotated[str | None, Cookie(alias="stratum_admin_session")] = None,
) -> User:
    # 1. Extract JWT from Bearer header OR cookie
    token = bearer.credentials if bearer is not None else admin_session
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, ...)
    
    # 2. Decode JWT
    try:
        payload = decode_access_token(token)
        subject = UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, ...) from error

    # 3. Fetch user from database
    user = db.get(User, subject)
    if user is None or user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, ...)
    
    return user
```

**Usage in routes:**
```python
@router.get("/users")
def list_users(admin: SuperAdmin, db: DbSession) -> list[User]:
    # admin is automatically injected User object
    return list(db.scalars(select(User)))
```

### CurrentUser Dependency - NOT IMPLEMENTED

**Search result:** `grep -r "CurrentUser" backend/` returns **0 results**

**What's needed:**

```python
# backend/app/api/dependencies.py (NEW CODE)

def require_current_user(
    db: DbSession,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_session: Annotated[str | None, Cookie(alias="stratum_session")] = None,
) -> User:
    # Same pattern as require_super_admin, but:
    # 1. Use "stratum_session" cookie instead of "stratum_admin_session"
    # 2. Check role == USER (not SUPER_ADMIN)
    # 3. Check account_status == APPROVED
    # 4. Check email_verified == True
    token = bearer.credentials if bearer is not None else user_session
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, ...)
    
    try:
        payload = decode_access_token(token)
        subject = UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, ...) from error

    user = db.get(User, subject)
    if user is None or user.role != UserRole.USER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, ...)
    if user.account_status != AccountStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not approved.")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified.")
    
    return user

CurrentUser = Annotated[User, Depends(require_current_user)]
```

### How to Implement Without Breaking Admin Auth

**✅ SAFE APPROACH:**

1. **Add new function** `require_current_user()` in `dependencies.py`
2. **Use different cookie name**: `stratum_session` (not `stratum_admin_session`)
3. **Check different role**: `UserRole.USER` (not `SUPER_ADMIN`)
4. **Additional checks**: account status, email verification
5. **Export new dependency**: `CurrentUser = Annotated[User, Depends(require_current_user)]`

**Why this is safe:**
- Different cookie names → no collision
- Different functions → admin auth untouched
- Same pattern → consistent with existing code
- JWT decoding logic reused → same security

**Usage in new client routes:**
```python
# backend/app/api/client.py (NEW FILE)
from app.api.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/api/v1/client", tags=["client"])

@router.get("/dashboard")
def get_dashboard_snapshot(current_user: CurrentUser, db: DbSession):
    # current_user is automatically injected User object (role=USER)
    # Fetch broker connection for this user
    # Return dashboard data
    ...
```

### Frontend Middleware Alignment

**Current middleware** (`src/middleware.ts`, lines 51-55):
```typescript
if (pathname.startsWith("/dashboard") && !hasSession) {
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}
```

**What it checks:**
- Only checks if `stratum_session` cookie exists
- Does NOT verify JWT (unlike admin routes)
- Assumes backend will validate on API calls

**This is correct!** Backend should validate JWT on every request, not middleware.

## 4. Existing Service Architecture

### Current Pattern

**Services are pure functions, not classes:**

```python
# backend/app/services/admin_bootstrap.py
def ensure_initial_super_admin(session: Session) -> User | None:
    # Pure function, no class
    ...

# backend/app/services/trading_engine.py
async def dispatch_engine_command(command: str, payload: dict) -> None:
    # Async function, uses httpx
    ...
```

### Service-to-Route Communication

**Pattern: Direct import and call**

```python
# In backend/app/main.py (startup)
from app.services.admin_bootstrap import ensure_initial_super_admin

@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as session:
        ensure_initial_super_admin(session)  # Direct call
    yield

# In backend/app/api/admin.py (route handler)
from app.services.trading_engine import dispatch_engine_command

@router.post("/strategies/{strategy_id}/start")
async def start_strategy(strategy_id: UUID, admin: SuperAdmin, db: DbSession):
    await dispatch_engine_command("start", {"strategy_id": str(strategy_id)})  # Direct call
    # Update database...
```

**No abstraction layer:**
- Routes import services directly
- Services accept db session as parameter
- No dependency injection for services
- No repository pattern
- No service interfaces/protocols

### Where Should Broker Logic Live?

**Option 1: app/services/brokers/ (RECOMMENDED)**

```
app/services/
├── admin_bootstrap.py       # Existing
├── trading_engine.py         # Existing
└── brokers/                  # NEW
    ├── __init__.py
    ├── base.py              # Abstract interface
    ├── zerodha.py
    ├── fyers.py
    └── ...
```

**Why this location:**
- ✅ Matches existing pattern (`app/services/`)
- ✅ Broker logic is business logic (not infrastructure)
- ✅ Services communicate with external APIs (like trading_engine.py)
- ✅ Can be imported directly by routes
- ✅ Easy to test in isolation

**Option 2: app/integrations/ (NOT RECOMMENDED)**

```
app/integrations/
└── brokers/
```

**Why NOT:**
- ❌ Creates new top-level category
- ❌ No existing "integrations" folder
- ❌ Breaks project convention
- ❌ Requires explaining why it's different from services

**Option 3: app/api/brokers/ (NOT RECOMMENDED)**

**Why NOT:**
- ❌ `app/api/` is for route handlers, not business logic
- ❌ Mixing concerns (routes + broker API clients)
- ❌ Harder to reuse broker logic from background jobs

### Justification for app/services/brokers/

**Existing evidence:**
1. **trading_engine.py** - External HTTP API integration → Lives in `services/`
2. **admin_bootstrap.py** - Business logic (user creation) → Lives in `services/`

**Broker integrations are:**
- External API communication (like trading_engine.py)
- Business logic (authentication, order placement)
- Reusable across routes and background jobs
- Testable in isolation

**Therefore:** `app/services/brokers/` is the correct location.

### Service Architecture Pattern

**Current pattern to follow:**

```python
# app/services/brokers/base.py
from abc import ABC, abstractmethod

class BrokerProvider(ABC):
    @abstractmethod
    async def connect(self, user_id: UUID, auth_code: str) -> dict:
        pass
    
    @abstractmethod
    async def get_positions(self, user_id: UUID) -> list[dict]:
        pass

# app/services/brokers/zerodha.py
class ZerodhaBroker(BrokerProvider):
    async def connect(self, user_id: UUID, auth_code: str) -> dict:
        # Implementation
        pass
    
    async def get_positions(self, user_id: UUID) -> list[dict]:
        # Implementation
        pass

# app/services/broker_manager.py
BROKERS = {
    "zerodha": ZerodhaBroker,
    "fyers": FyersBroker,
}

def get_broker(provider: str) -> BrokerProvider:
    return BROKERS[provider]()

# In route handler
from app.services.broker_manager import get_broker

@router.get("/brokers/{provider}/connect")
async def connect_broker(provider: str, user: CurrentUser, db: DbSession):
    broker = get_broker(provider)
    result = await broker.connect(user.id, request.query_params["code"])
    # ...
```

**This matches existing patterns:**
- Services are imported and called directly
- Async functions for I/O operations
- No global state
- Session passed as parameter when needed

## 5. Future Broker Requirements

Based on the existing project architecture and typical trading platform needs, the broker layer must support:

### 1. OAuth Login Flow
- **GET /brokers/{provider}/connect** - Generate OAuth URL
- **GET /brokers/{provider}/callback** - Handle OAuth callback
- Store access_token, refresh_token (encrypted)
- Set BrokerConnection.status = CONNECTED
- Set BrokerConnection.connected_at = now()

### 2. Token Management
- **Refresh tokens before expiry** (background job)
- **Handle token expiry gracefully** (401 → refresh → retry)
- **Store token metadata** (expires_at, last_refresh_at)
- **Revoke tokens on disconnect**

### 3. Profile & Account Info
- **GET /brokers/{provider}/profile** - User profile from broker
- **GET /brokers/{provider}/margins** - Available margins
- **GET /brokers/{provider}/limits** - Trading limits

### 4. Funds Management
- **GET /brokers/{provider}/funds** - Available funds
- **Margin available**
- **Collateral** (if applicable)

### 5. Holdings
- **GET /brokers/{provider}/holdings** - Long-term investments
- Symbol, quantity, average price, current price, P&L

### 6. Positions
- **GET /brokers/{provider}/positions** - Intraday/swing positions
- Symbol, quantity, buy/sell price, current price, P&L
- **Used by admin dashboard** (`GET /admin/connected-users` already shows connected users)

### 7. Order Management
- **POST /brokers/{provider}/orders** - Place order
- **GET /brokers/{provider}/orders** - List orders
- **GET /brokers/{provider}/orders/{order_id}** - Order details
- **PUT /brokers/{provider}/orders/{order_id}** - Modify order
- **DELETE /brokers/{provider}/orders/{order_id}** - Cancel order
- **Support:** Market, Limit, SL, SL-M orders

### 8. Market Data
- **GET /brokers/{provider}/quotes** - Real-time quotes
- **GET /brokers/{provider}/ltp** - Last traded price
- **GET /brokers/{provider}/instruments** - Available instruments

### 9. Historical Data
- **GET /brokers/{provider}/historical** - OHLCV candles
- Support multiple timeframes (1m, 5m, 15m, 1h, 1d)
- Date range queries

### 10. WebSocket Streaming (Future)
- **WS /brokers/{provider}/stream** - Real-time ticks
- Order updates
- Position updates
- Market data streaming

### 11. Strategy Execution Integration
- **Called by trading engine** (referenced in `trading_engine.py`)
- Place orders on behalf of strategy
- Monitor positions
- Square off positions on strategy stop

### 12. Broker Disconnection
- **POST /brokers/{provider}/disconnect** - Revoke tokens
- Set BrokerConnection.status = DISCONNECTED
- Clear credentials
- Notify user

### 13. Error Handling
- **Network failures** - Retry with exponential backoff
- **Rate limiting** - Queue requests, respect broker limits
- **Invalid tokens** - Auto-refresh
- **Broker maintenance** - Graceful degradation

### 14. Audit & Logging
- Log all broker API calls
- Track response times
- Monitor error rates
- Alert on credential expiry

## 6. Best Folder Structure

### Recommended Structure (Matches Existing Architecture)

```
backend/app/
├── api/
│   ├── admin.py                    # Existing
│   ├── client.py                   # NEW: User-facing endpoints
│   └── dependencies.py             # Add CurrentUser dependency
├── models/
│   └── domain.py                   # Extend BrokerConnection model
├── schemas/
│   ├── admin.py                    # Existing
│   ├── client.py                   # NEW: Client response schemas
│   └── broker.py                   # NEW: Broker-specific schemas
├── services/
│   ├── admin_bootstrap.py          # Existing
│   ├── trading_engine.py           # Existing
│   ├── brokers/                    # NEW: Broker integrations
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract BrokerProvider
│   │   ├── zerodha.py
│   │   ├── fyers.py
│   │   ├── groww.py
│   │   ├── dhan.py
│   │   └── angel_one.py
│   ├── broker_manager.py           # NEW: Factory for broker selection
│   └── crypto.py                   # NEW: Credential encryption utils
└── core/
    ├── config.py                   # Add broker API keys
    └── security.py                 # Existing
```

### File-by-File Justification

#### backend/app/api/client.py (NEW)
**Why:** Separate user endpoints from admin endpoints
```python
router = APIRouter(prefix="/api/v1/client", tags=["client"])

@router.get("/dashboard")
def get_dashboard_snapshot(user: CurrentUser, db: DbSession): ...

@router.get("/brokers/{provider}/connect")
async def initiate_broker_oauth(provider: str, user: CurrentUser): ...

@router.get("/brokers/{provider}/callback")
async def broker_oauth_callback(provider: str, code: str, state: str, db: DbSession): ...
```

#### backend/app/services/brokers/ (NEW DIRECTORY)
**Why:** Matches existing service pattern, groups broker implementations

**base.py:**
```python
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

class BrokerProvider(ABC):
    @abstractmethod
    async def get_auth_url(self, user_id: UUID, redirect_uri: str) -> str: pass
    
    @abstractmethod
    async def handle_callback(self, code: str, state: str) -> dict[str, Any]: pass
    
    @abstractmethod
    async def get_profile(self, user_id: UUID) -> dict: pass
    
    @abstractmethod
    async def get_positions(self, user_id: UUID) -> list[dict]: pass
    
    @abstractmethod
    async def place_order(self, user_id: UUID, order: dict) -> dict: pass
    
    @abstractmethod
    async def disconnect(self, user_id: UUID) -> None: pass
```

**zerodha.py, fyers.py, etc.:**
```python
from app.services.brokers.base import BrokerProvider

class ZerodhaBroker(BrokerProvider):
    async def get_auth_url(self, user_id: UUID, redirect_uri: str) -> str:
        # Zerodha-specific OAuth implementation
        ...
    
    async def get_positions(self, user_id: UUID) -> list[dict]:
        # Call Zerodha API
        ...
```

#### backend/app/services/broker_manager.py (NEW)
**Why:** Factory pattern for broker selection (DRY principle)
```python
from app.services.brokers.base import BrokerProvider
from app.services.brokers import zerodha, fyers, groww

BROKERS: dict[str, type[BrokerProvider]] = {
    "zerodha": zerodha.ZerodhaBroker,
    "fyers": fyers.FyersBroker,
    "groww": groww.GrowwBroker,
}

def get_broker(provider: str) -> BrokerProvider:
    if provider not in BROKERS:
        raise ValueError(f"Unsupported broker: {provider}")
    return BROKERS[provider]()
```

#### backend/app/schemas/broker.py (NEW)
**Why:** Broker-specific request/response schemas
```python
class BrokerConnectionOutput(BaseModel):
    provider: str
    status: BrokerStatus
    connected_at: datetime | None

class PositionOutput(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    pnl: float

class OrderInput(BaseModel):
    symbol: str
    quantity: int
    order_type: str  # MARKET, LIMIT
    side: str  # BUY, SELL
    price: float | None = None
```

#### backend/app/schemas/client.py (NEW)
**Why:** Client dashboard response schemas
```python
class DashboardSnapshotOutput(BaseModel):
    profile: dict | None
    broker: dict | None
    strategy: dict | None
    pnl: dict | None
    positions: dict | None
```

#### backend/app/services/crypto.py (NEW)
**Why:** Centralized credential encryption
```python
from cryptography.fernet import Fernet
from app.core.config import get_settings

def encrypt_token(token: str) -> str:
    # Use Fernet symmetric encryption
    ...

def decrypt_token(encrypted: str) -> str:
    ...
```

### Why This Structure Matches Existing Architecture

1. **API separation** - `admin.py` vs `client.py` (like admin portal vs user dashboard in frontend)
2. **Services in `app/services/`** - Follows `trading_engine.py` pattern
3. **Factory pattern** - `broker_manager.py` centralizes broker selection
4. **No new top-level directories** - Everything fits existing structure
5. **Schemas separated by domain** - `admin.py`, `client.py`, `broker.py`

## 7. Potential Conflicts

### 1. Database Schema Extension Needed

**Current limitation:**
```python
class BrokerConnection(Base):
    provider: Mapped[str]
    status: Mapped[BrokerStatus]
    connected_at: Mapped[datetime | None]
    # ❌ No fields for tokens, metadata
```

**Required fields:**
```python
access_token_encrypted: Mapped[str | None]
refresh_token_encrypted: Mapped[str | None]
token_expires_at: Mapped[datetime | None]
last_sync_at: Mapped[datetime | None]
broker_user_id: Mapped[str | None]  # Broker's internal user ID
metadata: Mapped[dict | None]  # JSON field for broker-specific data
```

**Migration required:** New Alembic migration to add these fields

### 2. CurrentUser Dependency Missing

**Impact:** All `/api/v1/client/*` endpoints will fail until implemented

**Solution:** Add `require_current_user()` function in `dependencies.py` (see Section 3)

### 3. User Authentication Endpoints Missing

**Frontend expects:**
- `POST /api/v1/client/auth/login`
- `POST /api/v1/client/auth/register`
- `POST /api/v1/client/auth/logout`

**Impact:** Users cannot log in, broker integration cannot proceed

**Priority:** CRITICAL - Must implement before broker integrations

### 4. JWT Secret in Frontend Middleware

**Security risk:** `JWT_SECRET_KEY` exposed in `.env.local`

**Solution:** Remove JWT verification from frontend middleware, let backend handle it

**Change required:** Update `src/middleware.ts` to only check cookie presence for user routes

### 5. No Background Job Infrastructure

**Need:** Token refresh requires background jobs (every 6-24 hours)

**Options:**
- **APScheduler** - Simple, runs in-process
- **Celery** - Robust, requires Redis/RabbitMQ
- **Cron job** - External script hitting internal endpoint

**Impact:** Tokens will expire, users disconnected until manual re-auth

### 6. No Credential Encryption

**Risk:** Tokens stored in plain text = security breach

**Solution:** Use `cryptography` library (Fernet or AES-256-GCM)

**Store encryption key in:** Environment variable (production: secret manager)

### 7. No Rate Limiting

**Risk:** Broker APIs have strict rate limits (e.g., 10 req/sec)

**Impact:** API ban, user disconnection

**Solution:** Implement Redis-based rate limiter or async queue

### 8. No WebSocket Infrastructure

**Need:** Real-time market data, order updates

**Current:** FastAPI supports WebSockets, but no implementation yet

**Impact:** No real-time features until WebSocket layer added

### 9. Strategy Execution Unclear

**Current:** `trading_engine.py` sends HTTP commands to `TRADING_ENGINE_URL`

**Question:** Does trading engine place broker orders, or does backend?

**Conflict:** If trading engine places orders, it needs broker credentials

**Solution:** Define clear boundary - likely backend handles broker API, engine makes decisions

### 10. No Error Recovery

**Missing:**
- Retry logic for network failures
- Circuit breaker for broker downtime
- Fallback responses when broker unavailable

**Impact:** Poor user experience, frequent errors

## 8. Recommendations

### As Lead Architect, Here's the Implementation Plan

---

### Phase 1: Foundation (Week 1) - CRITICAL

**Goal:** Enable user authentication and basic broker connection tracking

**Tasks:**
1. ✅ **Implement CurrentUser dependency** (`dependencies.py`)
   - Copy `require_super_admin()` pattern
   - Check `role=USER`, `account_status=APPROVED`, `email_verified=True`
   - Use `stratum_session` cookie

2. ✅ **Create user auth endpoints** (`api/client.py`)
   ```python
   POST /api/v1/client/auth/login
   POST /api/v1/client/auth/register
   POST /api/v1/client/auth/logout
   GET /api/v1/client/auth/session
   ```

3. ✅ **Extend BrokerConnection model** (Alembic migration)
   ```python
   access_token_encrypted: TEXT
   refresh_token_encrypted: TEXT
   token_expires_at: TIMESTAMP
   broker_user_id: VARCHAR(128)
   metadata: JSONB
   ```

4. ✅ **Add credential encryption** (`services/crypto.py`)
   ```python
   encrypt_token(token: str) -> str
   decrypt_token(encrypted: str) -> str
   ```

5. ✅ **Implement dashboard endpoint**
   ```python
   GET /api/v1/client/dashboard
   # Returns: broker status, profile, positions summary
   ```

**Deliverable:** Users can log in, see dashboard (with stub data for broker status)

---

### Phase 2: Broker Base Architecture (Week 2)

**Goal:** Create extensible broker integration framework

**Tasks:**
1. ✅ **Create broker service structure**
   ```
   app/services/brokers/
   ├── __init__.py
   ├── base.py          # Abstract BrokerProvider interface
   └── ...
   ```

2. ✅ **Define BrokerProvider interface** (`base.py`)
   ```python
   class BrokerProvider(ABC):
       @abstractmethod
       async def get_auth_url(...) -> str
       @abstractmethod
       async def handle_callback(...) -> dict
       @abstractmethod
       async def get_profile(...) -> dict
       @abstractmethod
       async def get_positions(...) -> list
       @abstractmethod
       async def place_order(...) -> dict
       @abstractmethod
       async def disconnect(...) -> None
   ```

3. ✅ **Create broker factory** (`broker_manager.py`)
   ```python
   BROKERS = {"zerodha": ZerodhaBroker, ...}
   def get_broker(provider: str) -> BrokerProvider
   ```

4. ✅ **Add broker connection endpoints**
   ```python
   GET /api/v1/client/brokers/{provider}/connect
   GET /api/v1/client/brokers/{provider}/callback
   POST /api/v1/client/brokers/{provider}/disconnect
   ```

5. ✅ **Create broker schemas** (`schemas/broker.py`)

**Deliverable:** Framework ready, can add brokers by implementing interface

---

### Phase 3: First Broker - Zerodha (Week 3)

**Goal:** Validate architecture with most popular Indian broker

**Tasks:**
1. ✅ **Install Zerodha SDK** (`pip install kiteconnect`)

2. ✅ **Implement ZerodhaBroker** (`services/brokers/zerodha.py`)
   ```python
   class ZerodhaBroker(BrokerProvider):
       def __init__(self):
           self.api_key = get_settings().zerodha_api_key
           self.api_secret = get_settings().zerodha_api_secret
       
       async def get_auth_url(self, user_id, redirect_uri):
           kite = KiteConnect(api_key=self.api_key)
           return kite.login_url()
       
       async def handle_callback(self, code, state):
           # Exchange code for access_token
           # Store encrypted in BrokerConnection
           ...
   ```

3. ✅ **Add Zerodha to broker factory**
   ```python
   BROKERS = {"zerodha": ZerodhaBroker}
   ```

4. ✅ **Test complete OAuth flow**
   - User clicks "Connect Zerodha"
   - Redirects to Kite login
   - Callback stores tokens
   - Dashboard shows "Connected"

5. ✅ **Implement positions endpoint**
   ```python
   GET /api/v1/client/brokers/zerodha/positions
   ```

**Deliverable:** Zerodha fully functional, users can connect and see positions

---

### Phase 4: Additional Brokers (Week 4-5)

**Goal:** Add Fyers, Groww, Dhan, Angel One

**Tasks:**
1. ✅ **Fyers** - Use `from fyers_api import fyers`
2. ✅ **Groww** - Custom HTTP client (no official SDK)
3. ✅ **Dhan** - Use `from dhanhq import dhanhq`
4. ✅ **Angel One** - Use `from smartapi import SmartConnect`

**Pattern for each:**
```python
# 1. Create services/brokers/{provider}.py
# 2. Implement BrokerProvider interface
# 3. Add to BROKERS dict in broker_manager.py
# 4. Test OAuth flow
# 5. Test positions/orders API
```

**Deliverable:** All 5 brokers supported

---

### Phase 5: Token Management (Week 6)

**Goal:** Handle token expiry gracefully

**Tasks:**
1. ✅ **Add APScheduler** (`pip install apscheduler`)

2. ✅ **Create token refresh service** (`services/token_refresh.py`)
   ```python
   async def refresh_all_tokens():
       expiring_soon = get_connections_expiring_in(hours=2)
       for connection in expiring_soon:
           broker = get_broker(connection.provider)
           await broker.refresh_token(connection.user_id)
   ```

3. ✅ **Schedule background job** (`main.py`)
   ```python
   scheduler = AsyncIOScheduler()
   scheduler.add_job(refresh_all_tokens, 'interval', hours=1)
   scheduler.start()
   ```

4. ✅ **Add auto-refresh on 401**
   ```python
   # In broker base class
   async def _call_api(self, ...):
       try:
           return await self._make_request(...)
       except Unauthorized:
           await self.refresh_token(user_id)
           return await self._make_request(...)  # Retry
   ```

**Deliverable:** Tokens never expire, seamless user experience

---

### Phase 6: Advanced Features (Week 7-8)

**Goal:** Real-time data, order management

**Tasks:**
1. ✅ **Order placement** - Implement `place_order()` for all brokers
2. ✅ **Order management** - List, modify, cancel orders
3. ✅ **WebSocket streaming** (optional) - Real-time market data
4. ✅ **Strategy integration** - Trading engine can place orders via backend
5. ✅ **Rate limiting** - Redis-based request throttling
6. ✅ **Monitoring** - Log all broker API calls, track success/failure rates

**Deliverable:** Full-featured broker integration

---

### Design Principles

**1. Minimal Code Changes Per Broker**
- Abstract interface defined once
- Each broker = one Python file implementing interface
- Factory pattern → no changes to routes

**2. Zero Impact on Existing Code**
- New file: `api/client.py` (doesn't touch `admin.py`)
- New dependency: `CurrentUser` (doesn't touch `SuperAdmin`)
- New service folder: `services/brokers/` (doesn't touch existing services)

**3. Database-Agnostic**
- Use existing `BrokerConnection` model
- Extend with encrypted token fields
- No new tables needed

**4. Security-First**
- Encrypt all tokens at rest
- JWT validation on every request
- Rate limit broker API calls
- Audit log all sensitive operations

**5. Scalable Architecture**
- Async/await for I/O operations
- Factory pattern for broker selection
- Background jobs for token refresh
- Circuit breaker for broker downtime

---

### Code References

**Files to create:**
- `backend/app/api/client.py`
- `backend/app/services/brokers/base.py`
- `backend/app/services/brokers/zerodha.py` (and 4 others)
- `backend/app/services/broker_manager.py`
- `backend/app/services/crypto.py`
- `backend/app/schemas/broker.py`
- `backend/app/schemas/client.py`

**Files to modify:**
- `backend/app/api/dependencies.py` - Add `require_current_user()`
- `backend/app/models/domain.py` - Extend `BrokerConnection`
- `backend/app/main.py` - Include `client_router`, start scheduler
- `backend/app/core/config.py` - Add broker API keys

**Alembic migration:**
- `backend/alembic/versions/20260723_0002_extend_broker_connection.py`

---

**End of Broker Analysis**
