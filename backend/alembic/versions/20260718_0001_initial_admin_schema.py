"""initial admin schema

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260718_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role = sa.Enum("USER", "ADMIN", "SUPER_ADMIN", name="user_role")
    account_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="account_status")
    subscription_status = sa.Enum("INACTIVE", "ACTIVE", name="subscription_status")
    broker_status = sa.Enum("DISCONNECTED", "CONNECTED", name="broker_status")
    strategy_status = sa.Enum("STOPPED", "RUNNING", name="strategy_status")
    execution_action = sa.Enum("STRATEGY_STARTED", "STRATEGY_STOPPED", "FORCE_SQUARE_OFF", name="execution_action")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("account_status", account_status, nullable=False),
        sa.Column("subscription_status", subscription_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_table(
        "broker_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", broker_status, nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_broker_connection_user_provider"),
    )
    op.create_index("ix_broker_connections_user_id", "broker_connections", ["user_id"], unique=False)
    op.create_table(
        "strategies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("script_filename", sa.String(length=260), nullable=False),
        sa.Column("script_storage_key", sa.String(length=512), nullable=False),
        sa.Column("status", strategy_status, nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("script_storage_key"),
    )
    op.create_table(
        "execution_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", execution_action, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("strategy_id", sa.Uuid(), nullable=True),
        sa.Column("initiated_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_logs_action", "execution_logs", ["action"], unique=False)
    op.create_index("ix_execution_logs_created_at", "execution_logs", ["created_at"], unique=False)
    op.create_table(
        "announcements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcements_created_at", "announcements", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_announcements_created_at", table_name="announcements")
    op.drop_table("announcements")
    op.drop_index("ix_execution_logs_created_at", table_name="execution_logs")
    op.drop_index("ix_execution_logs_action", table_name="execution_logs")
    op.drop_table("execution_logs")
    op.drop_table("strategies")
    op.drop_index("ix_broker_connections_user_id", table_name="broker_connections")
    op.drop_table("broker_connections")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    sa.Enum(name="execution_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="strategy_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="broker_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscription_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="account_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
