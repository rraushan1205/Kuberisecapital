from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import SubscriptionPlanTier, SubscriptionRequestStatus


class SubscriptionPlanOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tier: SubscriptionPlanTier
    capital: int
    nifty_lots: int
    sensex_lots: int
    bank_nifty_lots: int
    is_active: bool


class SubscriptionRequestInput(BaseModel):
    plan_id: UUID


class SubscriptionRequestOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    plan_id: UUID
    status: SubscriptionRequestStatus
    requested_at: datetime
    reviewed_at: datetime | None
    reviewed_by_id: UUID | None
    notes: str | None


class SubscriptionRequestWithDetailsOutput(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str
    user_full_name: str | None
    plan_tier: SubscriptionPlanTier
    plan_capital: int
    current_plan_tier: SubscriptionPlanTier | None
    status: SubscriptionRequestStatus
    requested_at: datetime
    reviewed_at: datetime | None
    reviewed_by_id: UUID | None
    notes: str | None


class ApproveSubscriptionRequestInput(BaseModel):
    notes: str | None = Field(None, max_length=500)


class RejectSubscriptionRequestInput(BaseModel):
    notes: str = Field(min_length=1, max_length=500)
