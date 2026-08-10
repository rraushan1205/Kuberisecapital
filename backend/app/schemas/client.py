from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class ClientLoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ClientRefreshInput(BaseModel):
    refresh_token: str


class ClientSessionOutput(BaseModel):
    user_id: UUID
    email: EmailStr
    account_status: str
    access_token: str
    refresh_token: str


# ─────────────────────────────────────────────────────────────────────────────
# Broker API Key Management
# ─────────────────────────────────────────────────────────────────────────────

class BrokerApiKeyInput(BaseModel):
    """Input schema for storing broker API credentials"""
    provider: str = Field(min_length=1, max_length=64, description="Broker provider name (e.g., 'fyers', 'zerodha')")
    api_key: str = Field(min_length=1, description="Broker API key")
    api_secret: str = Field(min_length=1, description="Broker API secret")


class BrokerApiKeyOutput(BaseModel):
    """Output schema for broker API key (with masked credentials)"""
    id: UUID
    provider: str
    api_key_masked: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Strategy Execution Management
# ─────────────────────────────────────────────────────────────────────────────

class StrategyControlRequest(BaseModel):
    """Request to start a strategy"""
    broker: str | None = None  # Optional broker override


class StrategyStateResponse(BaseModel):
    """Response showing current strategy execution state"""
    strategy_id: int
    status: str  # running, stopped, error, idle
    broker: str
    has_open_position: bool
    position_symbol: str | None = None
    position_side: str | None = None
    position_qty: int | None = None
    position_entry_price: float | None = None
    position_entry_time: datetime | None = None
    target_price: float | None = None
    stoploss_price: float | None = None
    last_signal_candle: datetime | None = None
    last_signal_type: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool  # Whether actively running in scheduler
    
    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Enhanced User Profile
# ─────────────────────────────────────────────────────────────────────────────

class EnhancedProfileOutput(BaseModel):
    """Enhanced user profile with broker authentication summary"""
    user_id: UUID
    email: str
    full_name: str | None
    account_status: str
    subscription_status: str
    connected_brokers: list[str]  # List of provider names with OAuth connections
    stored_api_keys: list[str]    # List of provider names with API keys stored
    last_broker_used: str | None
    login_method: str | None
    created_at: datetime
    last_login_at: datetime | None

    class Config:
        from_attributes = True
