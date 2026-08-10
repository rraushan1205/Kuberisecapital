"""
Pydantic schemas for strategy management - admin uploads strategies,
assigns them to users with configurations.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Strategy Definition Schemas (Admin uploads strategies)
# ============================================================================

class StrategyDefinitionBase(BaseModel):
    name: str = Field(..., max_length=100, description="Unique strategy name")
    description: str | None = Field(None, description="Strategy description")
    code: str = Field(..., description="Python strategy code")
    config_schema: dict[str, Any] | None = Field(None, description="JSON schema for strategy configuration")


class StrategyDefinitionCreate(StrategyDefinitionBase):
    pass


class StrategyDefinitionUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    code: str | None = None
    config_schema: dict[str, Any] | None = None
    is_active: bool | None = None


class StrategyDefinitionResponse(StrategyDefinitionBase):
    id: int
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StrategyDefinitionListResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# User Strategy Permission Schemas (User grants admin permission to trade)
# ============================================================================

class UserStrategyPermissionBase(BaseModel):
    allow_admin_trading: bool = Field(default=False, description="Whether admin can trade on user's behalf")
    max_daily_loss: float | None = Field(None, ge=0, description="Maximum daily loss limit")
    max_position_size: float | None = Field(None, ge=0, description="Maximum position size limit")


class UserStrategyPermissionUpdate(UserStrategyPermissionBase):
    pass


class UserStrategyPermissionResponse(UserStrategyPermissionBase):
    id: int
    user_id: UUID
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# User Strategy Assignment Schemas (Admin assigns strategies to users)
# ============================================================================

class UserStrategyAssignmentBase(BaseModel):
    strategy_def_id: int = Field(..., description="Strategy definition ID")
    config: dict[str, Any] | None = Field(None, description="Strategy configuration for this user")


class UserStrategyAssignmentCreate(UserStrategyAssignmentBase):
    user_id: UUID = Field(..., description="User to assign strategy to")


class UserStrategyAssignmentUpdate(BaseModel):
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class UserStrategyAssignmentResponse(UserStrategyAssignmentBase):
    id: int
    user_id: UUID
    assigned_by: UUID | None
    assigned_at: datetime
    is_active: bool
    started_at: datetime | None
    stopped_at: datetime | None

    class Config:
        from_attributes = True


class UserStrategyAssignmentDetailResponse(UserStrategyAssignmentResponse):
    """Extended response with strategy details"""
    strategy_name: str
    strategy_description: str | None

    class Config:
        from_attributes = True


# ============================================================================
# Bulk Assignment Schemas
# ============================================================================

class BulkAssignmentRequest(BaseModel):
    """Assign a strategy to multiple users at once"""
    user_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    strategy_def_id: int
    config: dict[str, Any] | None = None


class BulkAssignmentResponse(BaseModel):
    """Result of bulk assignment operation"""
    total_requested: int
    successful: int
    failed: int
    errors: list[dict[str, str]] = Field(default_factory=list)


# ============================================================================
# Strategy Control Schemas (Start/Stop strategies)
# ============================================================================

class StrategyControlRequest(BaseModel):
    """Request to start or stop a user's assigned strategy"""
    user_id: UUID
    assignment_id: int


class StrategyControlResponse(BaseModel):
    """Response after starting/stopping a strategy"""
    assignment_id: int
    user_id: UUID
    strategy_name: str
    is_active: bool
    message: str


# ============================================================================
# Statistics and Monitoring Schemas
# ============================================================================

class StrategyUsageStats(BaseModel):
    """Statistics about a strategy's usage"""
    strategy_id: int
    strategy_name: str
    total_assignments: int
    active_assignments: int
    inactive_assignments: int


class UserStrategyOverview(BaseModel):
    """Overview of a user's strategy assignments"""
    user_id: UUID
    user_email: str
    user_full_name: str | None
    has_permission: bool
    total_assignments: int
    active_assignments: int
