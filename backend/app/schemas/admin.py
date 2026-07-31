from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.domain import AccountStatus, StrategyStatus, SubscriptionStatus, UserRole


class AdminLoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class AdminRefreshInput(BaseModel):
    refresh_token: str


class AdminSessionOutput(BaseModel):
    user_id: UUID
    email: EmailStr
    role: UserRole


class AdminAuthOutput(AdminSessionOutput):
    access_token: str
    refresh_token: str


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    email_verified: bool
    account_status: AccountStatus
    subscription_status: SubscriptionStatus
    created_at: datetime


class StrategyOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    script_filename: str
    status: StrategyStatus
    created_at: datetime


class ExecutionLogOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: str
    message: str
    strategy_id: UUID | None
    initiated_by_id: UUID
    created_at: datetime


class AnnouncementInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=5000)


class AnnouncementOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    message: str
    created_by_id: UUID
    created_at: datetime


class DashboardStatsOutput(BaseModel):
    """Admin dashboard statistics"""
    total_users: int
    pending_registrations: int
    active_subscriptions: int
    active_strategies: int
    total_execution_logs: int


class UserDetailOutput(BaseModel):
    """Detailed user information including subscription details"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    email_verified: bool
    account_status: AccountStatus
    subscription_status: SubscriptionStatus
    created_at: datetime
    last_login_at: datetime | None
    
    # Current subscription plan details
    current_plan_id: UUID | None
    current_plan_tier: str | None
    current_plan_capital: int | None
    current_plan_nifty_lots: int | None
    current_plan_sensex_lots: int | None
    current_plan_bank_nifty_lots: int | None

    # Subscription request history
    pending_request_id: UUID | None
    pending_request_plan_tier: str | None


class UpdateUserSubscriptionInput(BaseModel):
    """Input for updating a user's subscription plan"""
    plan_id: UUID
    notes: str | None = Field(None, max_length=1000)
