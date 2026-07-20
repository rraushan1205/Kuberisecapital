from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.domain import AccountStatus, BrokerStatus, StrategyStatus, SubscriptionStatus, UserRole


class AdminLoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class AdminSessionOutput(BaseModel):
    user_id: UUID
    email: EmailStr
    role: UserRole


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


class ConnectedUserOutput(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str | None
    provider: str
    status: BrokerStatus
    connected_at: datetime | None


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
