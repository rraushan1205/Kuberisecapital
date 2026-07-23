# Stratum Broker Foundation - Implementation Summary

**Created:** 2026-07-23  
**Purpose:** Document the broker integration architecture foundation

---

## Overview

This document describes the broker foundation architecture implemented for the Stratum trading platform. This foundation provides a clean, extensible framework for integrating multiple broker providers (Zerodha, Fyers, Groww, Dhan, Angel One, etc.) without requiring changes to existing code when adding new brokers.

**What was implemented:**
- Abstract broker interface (BrokerProvider)
- Exception hierarchy for broker errors
- Shared types and constants
- Broker registry system
- Broker manager factory
- Comprehensive docstrings and examples

**What was NOT implemented** (as per requirements):
- No OAuth implementation
- No broker SDKs installed
- No API routes created
- No database migrations
- No broker-specific implementations

---

## Architecture Components

### 1. Base Interface (`base.py`)

**Purpose:** Defines the contract that all broker implementations must follow.

**Key Features:**
- Abstract base class using Python's ABC
- 20+ abstract methods covering all broker capabilities
- Property methods for broker metadata (provider_name, display_name)
- Comprehensive docstrings with examples and exception documentation

**Capabilities Defined:**

**Authentication:**
- `get_auth_url()` - Generate OAuth URL
- `handle_oauth_callback()` - Exchange code for tokens
- `refresh_access_token()` - Refresh expired tokens
- `revoke_token()` - Disconnect and revoke access

**Account Information:**
- `get_profile()` - Fetch user profile from broker
- `get_funds()` - Get available funds and margins

**Portfolio:**
- `get_holdings()` - Fetch long-term holdings
- `get_positions()` - Get open trading positions

**Order Management:**
- `place_order()` - Place new order
- `modify_order()` - Modify pending order
- `cancel_order()` - Cancel pending order
- `get_orders()` - List all orders
- `get_order_details()` - Get specific order details

**Market Data:**
- `get_quotes()` - Real-time quotes
- `get_historical_data()` - OHLCV candle data

**WebSocket (Optional):**
- `subscribe_to_ticks()` - Subscribe to real-time ticks
- `unsubscribe_from_ticks()` - Unsubscribe from ticks

**Design Decision:**
- Uses async/await for all I/O operations (matches existing trading_engine.py)
- Methods accept user_id and access_token explicitly (no hidden state)
- Returns standardized types (from types.py)
- Raises specific exceptions (from exceptions.py)

---

### 2. Exception Hierarchy (`exceptions.py`)

**Purpose:** Structured error handling for broker operations.

**Exception Tree:**
```
BrokerError (base)
├── BrokerNotFoundError
├── BrokerAuthenticationError
│   ├── BrokerTokenExpiredError
│   └── BrokerTokenInvalidError
├── BrokerConnectionError
│   ├── BrokerTimeoutError
│   └── BrokerUnavailableError
├── BrokerRateLimitError
├── BrokerValidationError
└── BrokerOperationError
    ├── BrokerInsufficientFundsError
    ├── BrokerOrderRejectedError
    └── BrokerMarketClosedError
```

**Design Decisions:**
- All exceptions inherit from `BrokerError` for easy catching
- Each exception stores context (provider, user_id, details dict)
- Exceptions map to HTTP status codes:
  - `BrokerNotFoundError` → 404
  - `BrokerAuthenticationError` → 401
  - `BrokerValidationError` → 400
  - `BrokerConnectionError` → 502
  - `BrokerRateLimitError` → 429
- Follows existing pattern from trading_engine.py (raises HTTPException)

**Example Usage:**
```python
try:
    positions = await broker.get_positions(user_id, access_token)
except BrokerTokenExpiredError:
    # Auto-refresh token
    new_token = await broker.refresh_access_token(user_id, refresh_token)
    positions = await broker.get_positions(user_id, new_token)
except BrokerConnectionError as e:
    # Log and return 502
    logger.error(f"Broker API unreachable: {e}")
    raise HTTPException(502, "Broker service unavailable")
```

---

### 3. Shared Types (`types.py`)

**Purpose:** Standard data structures for broker operations.

**Enums Defined:**
- `OrderType` - MARKET, LIMIT, STOP_LOSS, STOP_LOSS_MARKET
- `OrderSide` - BUY, SELL
- `OrderStatus` - PENDING, OPEN, COMPLETE, CANCELLED, REJECTED
- `OrderValidity` - DAY, IOC, GTC
- `PositionType` - INTRADAY, DELIVERY, CARRYFORWARD
- `ExchangeSegment` - NSE_EQ, NSE_FO, BSE_EQ, MCX_FO, etc.
- `ProductType` - INTRADAY, DELIVERY, CARRYFORWARD, MARGIN
- `Interval` - 1m, 5m, 15m, 1h, 1d, etc. (for candles)

**TypedDict Structures:**
- `BrokerProfile` - User profile from broker
- `Funds` - Available funds and margins
- `Position` - Trading position details
- `Holding` - Long-term holding details
- `Order` - Order information
- `Quote` - Real-time market quote
- `Candle` - OHLCV candle data
- `OrderRequest` - Order placement input

**Design Decisions:**
- Uses `str` enums for JSON serialization (matches existing domain.py pattern)
- TypedDict provides type hints without runtime overhead
- `total=False` for optional fields
- Follows Indian market conventions (NSE, BSE, MCX segments)

---

### 4. Constants (`constants.py`)

**Purpose:** Centralized configuration values.

**Categories:**

**Timeouts:**
- `DEFAULT_API_TIMEOUT_SECONDS = 30`
- `QUOTE_API_TIMEOUT_SECONDS = 10`
- `HISTORICAL_DATA_TIMEOUT_SECONDS = 60`
- `WEBSOCKET_CONNECT_TIMEOUT_SECONDS = 15`

**Rate Limiting:**
- `DEFAULT_RATE_LIMIT_PER_SECOND = 10`
- `RATE_LIMIT_RETRY_ATTEMPTS = 3`
- `RATE_LIMIT_BACKOFF_SECONDS = 5`

**Token Management:**
- `TOKEN_EXPIRY_BUFFER_SECONDS = 300` (refresh 5 min before expiry)
- `DEFAULT_TOKEN_VALIDITY_HOURS = 24`

**Retry Logic:**
- `MAX_RETRY_ATTEMPTS = 3`
- `INITIAL_RETRY_DELAY_SECONDS = 1`
- `RETRY_BACKOFF_MULTIPLIER = 2`

**Limits:**
- `MAX_ORDER_QUANTITY = 100000`
- `MAX_HISTORICAL_CANDLES = 5000`
- `MAX_SYMBOLS_PER_QUOTE_REQUEST = 500`

**Cache TTL:**
- `PROFILE_CACHE_TTL_SECONDS = 3600`
- `FUNDS_CACHE_TTL_SECONDS = 60`
- `HOLDINGS_CACHE_TTL_SECONDS = 300`

**Supported Brokers List:**
```python
SUPPORTED_BROKERS = [
    "zerodha", "fyers", "groww", "dhan", "angelone",
    "upstox", "5paisa", "aliceblue", "iifl", "kotak"
]
```

**Standard Error Messages:**
- Pre-defined error messages for consistent error handling

**Design Decisions:**
- All constants in UPPER_SNAKE_CASE (Python convention)
- Conservative default values (can be overridden per broker)
- Based on real-world broker API limitations

---

### 5. Broker Registry (`registry.py`)

**Purpose:** Centralized registration and discovery of broker implementations.

**Key Features:**
- Type-safe registration (validates BrokerProvider subclass)
- Singleton pattern via `get_global_registry()`
- Validates provider names (lowercase, URL-safe)
- Runtime validation of broker implementations
- Support for listing and querying registered brokers

**Core Methods:**
```python
class BrokerRegistry:
    def register(broker_class: Type[BrokerProvider]) -> None
    def unregister(provider_name: str) -> None
    def get(provider_name: str) -> Type[BrokerProvider]
    def is_registered(provider_name: str) -> bool
    def list_providers() -> list[str]
    def list_brokers() -> list[dict]
```

**Global Singleton:**
```python
def get_global_registry() -> BrokerRegistry
def reset_global_registry() -> None  # For testing
```

**Design Decisions:**
- Registry stores **classes**, not instances (factory pattern)
- Validates broker implementations at registration time
- Provider name must be lowercase and URL-safe
- Singleton pattern for application-wide registry
- Testable (can inject custom registry for tests)

**Example Usage:**
```python
# In app startup or broker implementation file
from app.services.brokers.registry import get_global_registry
from app.services.brokers.implementations.zerodha import ZerodhaBroker

registry = get_global_registry()
registry.register(ZerodhaBroker)
```

---

### 6. Broker Manager (`manager.py`)

**Purpose:** Factory for creating and managing broker instances.

**Key Features:**
- Factory pattern for broker instantiation
- Follows existing Stratum pattern (like get_settings())
- Uses @lru_cache for singleton behavior
- Stateless (creates fresh instances on demand)
- Provider name validation
- Broker metadata queries

**Core Methods:**
```python
class BrokerManager:
    def get_broker(provider_name: str) -> BrokerProvider
    def is_provider_supported(provider_name: str) -> bool
    def list_supported_providers() -> list[str]
    def list_available_brokers() -> list[dict]
    def get_broker_display_name(provider_name: str) -> str
    def validate_provider_name(provider_name: str) -> tuple[bool, str | None]
```

**Global Function:**
```python
@lru_cache(maxsize=1)
def get_broker_manager() -> BrokerManager
```

**Convenience Function:**
```python
def get_broker(provider_name: str) -> BrokerProvider
```

**Design Decisions:**
- Manager is the ONLY way routes should get brokers
- Creates fresh instances (brokers are stateless)
- Follows get_settings() pattern from core/config.py
- Normalizes provider names (lowercase, strip whitespace)
- Provides validation helpers for route handlers

**Example Usage in Route:**
```python
from app.services.brokers import get_broker_manager

@router.get("/brokers/{provider}/positions")
async def get_positions(provider: str, user: CurrentUser, db: DbSession):
    # Get the manager
    manager = get_broker_manager()
    
    # Validate provider
    is_valid, error = manager.validate_provider_name(provider)
    if not is_valid:
        raise HTTPException(400, error)
    
    # Get broker instance
    broker = manager.get_broker(provider)
    
    # Fetch stored credentials from database
    connection = db.query(BrokerConnection).filter_by(
        user_id=user.id,
        provider=provider
    ).first()
    
    if not connection:
        raise HTTPException(404, "Broker not connected")
    
    # Decrypt token (from future crypto service)
    access_token = decrypt_token(connection.access_token_encrypted)
    
    # Use the broker
    positions = await broker.get_positions(user.id, access_token)
    
    return {"positions": positions}
```

---

## How Future Brokers Plug In

### Step 1: Implement BrokerProvider

Create a new file in `backend/app/services/brokers/implementations/`:

```python
# backend/app/services/brokers/implementations/zerodha.py

from uuid import UUID
from datetime import datetime
from app.services.brokers.base import BrokerProvider
from app.services.brokers.types import (
    BrokerProfile, Funds, Position, Order, OrderRequest, Quote, Candle
)
from app.services.brokers.exceptions import (
    BrokerAuthenticationError, BrokerConnectionError
)

class ZerodhaBroker(BrokerProvider):
    """Zerodha Kite broker implementation."""
    
    @property
    def provider_name(self) -> str:
        return "zerodha"
    
    @property
    def display_name(self) -> str:
        return "Zerodha Kite"
    
    @property
    def supports_websocket(self) -> bool:
        return True
    
    async def get_auth_url(self, user_id: UUID, redirect_uri: str) -> str:
        # Zerodha-specific OAuth URL generation
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=settings.zerodha_api_key)
        return kite.login_url()
    
    async def handle_oauth_callback(self, code: str, state: str) -> dict[str, str]:
        # Exchange code for access token
        ...
    
    async def get_positions(self, user_id: UUID, access_token: str) -> list[Position]:
        # Fetch positions from Zerodha API
        ...
    
    # Implement all other abstract methods...
```

### Step 2: Register the Broker

In `backend/app/main.py` or a dedicated broker initialization file:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.brokers.registry import get_global_registry
from app.services.brokers.implementations.zerodha import ZerodhaBroker
from app.services.brokers.implementations.fyers import FyersBroker
# ... import other broker implementations

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register all brokers on startup
    registry = get_global_registry()
    registry.register(ZerodhaBroker)
    registry.register(FyersBroker)
    # ... register other brokers
    
    yield
    
    # Cleanup on shutdown (if needed)

app = FastAPI(lifespan=lifespan)
```

### Step 3: Use in Routes

No route changes needed! Existing routes automatically support the new broker:

```python
# This route works for ANY registered broker
@router.get("/brokers/{provider}/positions")
async def get_positions(provider: str, user: CurrentUser):
    manager = get_broker_manager()
    broker = manager.get_broker(provider)  # Auto-resolves to ZerodhaBroker if provider="zerodha"
    positions = await broker.get_positions(user.id, access_token)
    return positions
```

### That's It!

**Zero changes required to:**
- Existing routes
- Database models
- Other brokers
- Frontend code (just add to dropdown)

---

## Architectural Decisions Based on Existing Stratum Codebase

### 1. **Service Layer Pattern** (from `trading_engine.py`)

**Existing Code:**
```python
# backend/app/services/trading_engine.py
async def dispatch_engine_command(command: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    # ... implementation
```

**Broker Architecture:**
- Follows same pattern: services are pure async functions
- No complex DI framework
- Direct imports and calls
- Located in `app/services/` directory

### 2. **Settings Pattern** (from `core/config.py`)

**Existing Code:**
```python
# backend/app/core/config.py
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Broker Architecture:**
```python
# backend/app/services/brokers/manager.py
@lru_cache(maxsize=1)
def get_broker_manager() -> BrokerManager:
    return BrokerManager()
```

Rationale: Consistent with existing singleton pattern

### 3. **Enum Pattern** (from `models/domain.py`)

**Existing Code:**
```python
# backend/app/models/domain.py
class UserRole(str, enum.Enum):
    USER = "USER"
    SUPER_ADMIN = "SUPER_ADMIN"

class BrokerStatus(str, enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
```

**Broker Architecture:**
```python
# backend/app/services/brokers/types.py
class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
```

Rationale: Matches existing enum style (str enums for JSON compatibility)

### 4. **Exception Handling** (from `trading_engine.py`)

**Existing Code:**
```python
# backend/app/services/trading_engine.py
except httpx.HTTPError as error:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The trading engine did not accept the command.",
    ) from error
```

**Broker Architecture:**
- Custom exception hierarchy (BrokerError and subclasses)
- Route handlers catch and convert to HTTPException
- Structured error information (provider, user_id, details)

Rationale: More specific than HTTPException, but route handlers still raise HTTPException

### 5. **No Dependency Injection Framework**

**Existing Code:**
- Dependencies injected via FastAPI's `Depends()`
- Services imported directly
- No complex DI container

**Broker Architecture:**
- BrokerManager obtained via `get_broker_manager()` function
- Brokers created on-demand (factory pattern)
- Can inject custom registry for testing

Rationale: Maintains simplicity of existing architecture

### 6. **Database Model Extension** (not implemented yet, but designed for)

**Existing Code:**
```python
# backend/app/models/domain.py
class BrokerConnection(Base):
    provider: Mapped[str]
    status: Mapped[BrokerStatus]
    connected_at: Mapped[datetime | None]
```

**Future Extension Needed:**
```python
# Will need Alembic migration to add:
access_token_encrypted: Mapped[str | None]
refresh_token_encrypted: Mapped[str | None]
token_expires_at: Mapped[datetime | None]
broker_user_id: Mapped[str | None]
metadata: Mapped[dict | None]  # JSONB
```

Rationale: Extends existing model rather than creating new table

---

## File Structure

```
backend/app/services/brokers/
├── __init__.py              # Public API (exports get_broker_manager)
├── base.py                  # BrokerProvider abstract base class
├── exceptions.py            # Exception hierarchy
├── types.py                 # Shared types and enums
├── constants.py             # Shared constants
├── registry.py              # BrokerRegistry for registration
├── manager.py               # BrokerManager factory
└── implementations/         # Future broker implementations
    ├── __init__.py
    ├── zerodha.py
    ├── fyers.py
    ├── groww.py
    ├── dhan.py
    └── angelone.py
```

---

## Testing Strategy (Not Implemented, But Designed For)

### Unit Testing Brokers

```python
# tests/test_brokers/test_zerodha.py
import pytest
from app.services.brokers.implementations.zerodha import ZerodhaBroker
from app.services.brokers.exceptions import BrokerTokenExpiredError

@pytest.mark.asyncio
async def test_zerodha_get_positions_with_expired_token():
    broker = ZerodhaBroker()
    with pytest.raises(BrokerTokenExpiredError):
        await broker.get_positions(user_id, expired_token)
```

### Integration Testing with Mock Registry

```python
# tests/test_brokers/test_manager.py
from app.services.brokers.manager import BrokerManager
from app.services.brokers.registry import BrokerRegistry
from tests.mocks import MockBroker

def test_broker_manager_with_mock():
    # Create isolated registry
    registry = BrokerRegistry()
    registry.register(MockBroker)
    
    # Create manager with mock registry
    manager = BrokerManager(registry=registry)
    
    # Test
    broker = manager.get_broker("mock")
    assert isinstance(broker, MockBroker)
```

---

## Next Steps

### Phase 1: Authentication Infrastructure (Before Broker Implementation)

1. **Extend BrokerConnection model** (Alembic migration)
   ```python
   # Add fields: access_token_encrypted, refresh_token_encrypted,
   # token_expires_at, broker_user_id, metadata
   ```

2. **Create credential encryption service** (`app/services/crypto.py`)
   ```python
   def encrypt_token(token: str) -> str
   def decrypt_token(encrypted: str) -> str
   ```

3. **Implement CurrentUser dependency** (`app/api/dependencies.py`)
   ```python
   def require_current_user(...) -> User
   CurrentUser = Annotated[User, Depends(require_current_user)]
   ```

### Phase 2: First Broker Implementation (Zerodha)

1. **Install Zerodha SDK**
   ```bash
   pip install kiteconnect
   ```

2. **Create ZerodhaBroker class** (`implementations/zerodha.py`)
   - Implement all BrokerProvider methods
   - Handle Zerodha-specific data formats
   - Map Zerodha errors to broker exceptions

3. **Register broker in main.py**
   ```python
   registry.register(ZerodhaBroker)
   ```

4. **Create client API routes** (`app/api/client.py`)
   ```python
   GET /api/v1/client/brokers/{provider}/connect
   GET /api/v1/client/brokers/{provider}/callback
   GET /api/v1/client/brokers/{provider}/positions
   # ... etc
   ```

### Phase 3: Additional Brokers (Fyers, Groww, etc.)

For each new broker:
1. Create `implementations/{broker}.py`
2. Implement BrokerProvider interface
3. Register in main.py
4. No route changes needed!

### Phase 4: Advanced Features

1. **Token refresh background job** (APScheduler)
2. **Rate limiting** (Redis-based)
3. **WebSocket streaming**
4. **Caching layer** (Redis)
5. **Monitoring and alerting**

---

## Benefits of This Architecture

### 1. **Open/Closed Principle**
- Open for extension (add new brokers)
- Closed for modification (no changes to existing code)

### 2. **Single Responsibility**
- Each component has one job
- BrokerProvider: Defines interface
- BrokerRegistry: Manages registration
- BrokerManager: Creates instances
- Individual brokers: Implement integration

### 3. **Dependency Inversion**
- Routes depend on BrokerProvider (abstraction)
- Not on ZerodhaBroker or FyersBroker (concrete implementations)

### 4. **Easy Testing**
- Mock brokers for testing routes
- Test brokers in isolation
- Inject test registries

### 5. **Type Safety**
- Full type hints throughout
- Runtime validation in registry
- Mypy compatible

### 6. **Consistent with Existing Code**
- Follows trading_engine.py pattern
- Uses same enum style as domain.py
- Matches get_settings() singleton pattern
- No new architectural concepts

### 7. **Production Ready**
- Comprehensive error handling
- Detailed logging support
- Rate limiting constants
- Retry logic guidelines
- Security considerations (token encryption)

---

## Summary

The broker foundation provides a **production-quality, extensible architecture** for integrating multiple broker providers into the Stratum platform. It follows existing Stratum patterns while introducing clean abstractions that make adding new brokers trivial.

**Key Achievement:** Adding a new broker requires creating only ONE file and registering ONE class. Zero changes to routes, database, or other brokers.

**Next Action:** Begin Phase 1 (authentication infrastructure) followed by implementing the first broker (Zerodha) to validate the architecture.

---

**End of Broker Foundation Summary**
