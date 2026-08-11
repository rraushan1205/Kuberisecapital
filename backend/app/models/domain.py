import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class AccountStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SubscriptionStatus(str, enum.Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"


class BrokerStatus(str, enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"


class StrategyStatus(str, enum.Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"


class ExecutionAction(str, enum.Enum):
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    FORCE_SQUARE_OFF = "FORCE_SQUARE_OFF"


class SubscriptionPlanTier(str, enum.Enum):
    BASIC = "BASIC"
    PLUS = "PLUS"
    PRO = "PRO"
    ELITE = "ELITE"
    MAX = "MAX"


class SubscriptionRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LoginMethod(str, enum.Enum):
    """Method used for broker authentication"""
    OAUTH = "OAUTH"
    API_KEY = "API_KEY"


class RefreshToken(Base):
    """
    Refresh tokens for session management with inactivity-based expiration.
    Supports token rotation and reuse detection for security.
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_family_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, index=True)  # For detecting token reuse
    token_hash: Mapped[str] = mapped_column(String(512), unique=True, index=True)  # Hashed refresh token
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    absolute_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Session configuration
    inactivity_timeout_minutes: Mapped[int] = mapped_column()  # Role-based idle timeout
    absolute_max_hours: Mapped[int | None] = mapped_column(nullable=True)  # Optional hard limit
    
    # Status and metadata
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_info: Mapped[str | None] = mapped_column(String(512), nullable=True)  # User agent
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv4/IPv6
    
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    full_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.USER, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    account_status: Mapped[AccountStatus] = mapped_column(Enum(AccountStatus, name="account_status"), default=AccountStatus.PENDING)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus, name="subscription_status"), default=SubscriptionStatus.INACTIVE)
    current_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 2FA / Google Authenticator settings
    totp_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Broker authentication preferences
    login_method: Mapped[LoginMethod | None] = mapped_column(Enum(LoginMethod, name="login_method"), nullable=True)
    last_broker_used: Mapped[str | None] = mapped_column(String(64), nullable=True)

    current_plan: Mapped["SubscriptionPlan | None"] = relationship(foreign_keys=[current_plan_id])
    subscription_requests: Mapped[list["SubscriptionRequest"]] = relationship(back_populates="user", foreign_keys="[SubscriptionRequest.user_id]", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    broker_connections: Mapped[list["BrokerConnection"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    broker_api_keys: Mapped[list["BrokerApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    strategy_permission: Mapped["UserStrategyPermission | None"] = relationship(back_populates="user", uselist=False)
    strategy_assignments: Mapped[list["UserStrategyAssignment"]] = relationship(
        back_populates="user", 
        foreign_keys="[UserStrategyAssignment.user_id]",
        cascade="all, delete-orphan"
    )


class BrokerConnection(Base):
    __tablename__ = "broker_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_broker_connection_user_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[BrokerStatus] = mapped_column(Enum(BrokerStatus, name="broker_status"), default=BrokerStatus.DISCONNECTED)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    broker_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    broker_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped[User] = relationship(back_populates="broker_connections")


class BrokerApiKey(Base):
    """
    Stores encrypted API credentials for brokers that support API key authentication.
    Alternative to OAuth for brokers like Fyers, Zerodha, etc.
    """
    __tablename__ = "broker_api_keys"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_broker_api_key_user_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    api_key_encrypted: Mapped[str] = mapped_column(Text)
    api_secret_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="broker_api_keys")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    script_filename: Mapped[str] = mapped_column(String(260))
    script_storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    status: Mapped[StrategyStatus] = mapped_column(Enum(StrategyStatus, name="strategy_status"), default=StrategyStatus.STOPPED)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action: Mapped[ExecutionAction] = mapped_column(Enum(ExecutionAction, name="execution_action"), index=True)
    message: Mapped[str] = mapped_column(Text)
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    initiated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tier: Mapped[SubscriptionPlanTier] = mapped_column(Enum(SubscriptionPlanTier, name="subscription_plan_tier"), unique=True, index=True)
    capital: Mapped[int] = mapped_column()
    nifty_lots: Mapped[int] = mapped_column()
    sensex_lots: Mapped[int] = mapped_column()
    bank_nifty_lots: Mapped[int] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubscriptionRequest(Base):
    __tablename__ = "subscription_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscription_plans.id", ondelete="RESTRICT"))
    status: Mapped[SubscriptionRequestStatus] = mapped_column(Enum(SubscriptionRequestStatus, name="subscription_request_status"), default=SubscriptionRequestStatus.PENDING, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="subscription_requests", foreign_keys=[user_id])
    plan: Mapped[SubscriptionPlan] = relationship()
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])


class StrategyState(Base):
    """Tracks real-time state of strategy execution for each user"""
    __tablename__ = "strategy_state"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int] = mapped_column()
    broker: Mapped[str] = mapped_column(String(50))
    
    # Signal tracking
    last_signal_candle: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_signal_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Position tracking
    has_open_position: Mapped[bool] = mapped_column(Boolean, default=False)
    position_symbol: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position_side: Mapped[str | None] = mapped_column(String(10), nullable=True)
    position_qty: Mapped[int | None] = mapped_column(nullable=True)
    position_entry_price: Mapped[float | None] = mapped_column(nullable=True)
    position_entry_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entry_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # TP/SL tracking
    tp_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sl_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_price: Mapped[float | None] = mapped_column(nullable=True)
    stoploss_price: Mapped[float | None] = mapped_column(nullable=True)
    
    # Metadata
    status: Mapped[str] = mapped_column(String(20), default="idle")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_attempt_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'strategy_id', name='uq_user_strategy'),
    )


class StrategyDefinition(Base):
    """Admin-uploaded strategy definitions"""
    __tablename__ = "strategy_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    config_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    assignments: Mapped[list["UserStrategyAssignment"]] = relationship(back_populates="strategy_definition", cascade="all, delete-orphan")


class UserStrategyPermission(Base):
    """User permission for admin to trade on their behalf"""
    __tablename__ = "user_strategy_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    allow_admin_trading: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    max_daily_loss: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_position_size: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="strategy_permission")


class UserStrategyAssignment(Base):
    """Admin assigns strategies to users"""
    __tablename__ = "user_strategy_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_def_id: Mapped[int] = mapped_column(ForeignKey("strategy_definitions.id", ondelete="CASCADE"), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="strategy_assignments", foreign_keys=[user_id])
    strategy_definition: Mapped["StrategyDefinition"] = relationship(back_populates="assignments")

    __table_args__ = (
        UniqueConstraint('user_id', 'strategy_def_id', name='uq_user_strategy_assignment'),
    )
