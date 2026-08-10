"""
Shared test fixtures and utilities for strategy management tests.
"""
import os
import sys
from typing import Generator
from uuid import uuid4

# Set test environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-strategy-tests-0123456789abcdef")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdminPass123!")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.models.domain import (
    AccountStatus,
    StrategyDefinition,
    User,
    UserRole,
    UserStrategyAssignment,
    UserStrategyPermission,
)


def create_test_engine():
    """Create an in-memory SQLite engine for tests."""
    return create_engine("sqlite+pysqlite:///:memory:", echo=False)


def create_test_session(engine) -> Session:
    """Create a test database session."""
    Base.metadata.create_all(engine)
    return Session(engine)


def create_test_admin(session: Session) -> User:
    """Create a test admin user."""
    admin = User(
        id=uuid4(),
        email="testadmin@example.com",
        password_hash=hash_password("TestAdminPass123!"),
        role=UserRole.ADMIN,
        account_status=AccountStatus.APPROVED,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def create_test_user(session: Session, email: str = "testuser@example.com") -> User:
    """Create a test regular user."""
    user = User(
        id=uuid4(),
        email=email,
        password_hash=hash_password("TestUserPass123!"),
        role=UserRole.USER,
        account_status=AccountStatus.APPROVED,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_test_strategy_definition(
    session: Session, 
    admin: User,
    name: str = "Test Strategy",
    code: str = None
) -> StrategyDefinition:
    """Create a test strategy definition."""
    if code is None:
        code = """
import pandas as pd
from typing import Optional, Dict

async def check_for_signal(index_df, state, config, adapter, token):
    '''Test strategy that always returns None'''
    return None
"""
    
    strategy_def = StrategyDefinition(
        name=name,
        description="Test strategy for unit tests",
        code=code,
        config_schema={
            "type": "object",
            "properties": {
                "test_param": {"type": "integer", "minimum": 1, "maximum": 100}
            }
        },
        created_by=admin.id,
        is_active=True,
    )
    session.add(strategy_def)
    session.commit()
    session.refresh(strategy_def)
    return strategy_def


def create_test_user_permission(
    session: Session,
    user: User,
    allow_admin_trading: bool = True,
    max_daily_loss: float = 10000.0,
    max_position_size: float = 50000.0
) -> UserStrategyPermission:
    """Create a test user strategy permission."""
    permission = UserStrategyPermission(
        user_id=user.id,
        allow_admin_trading=allow_admin_trading,
        max_daily_loss=max_daily_loss,
        max_position_size=max_position_size,
    )
    session.add(permission)
    session.commit()
    session.refresh(permission)
    return permission


def create_test_assignment(
    session: Session,
    user: User,
    strategy_def: StrategyDefinition,
    admin: User,
    config: dict = None,
    is_active: bool = False
) -> UserStrategyAssignment:
    """Create a test user strategy assignment."""
    assignment = UserStrategyAssignment(
        user_id=user.id,
        strategy_def_id=strategy_def.id,
        config=config or {"test_param": 50},
        assigned_by=admin.id,
        is_active=is_active,
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment
