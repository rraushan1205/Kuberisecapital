"""drop broker connections table

Removes the broker_connections table (and its broker_status enum) introduced
for the Fyers OAuth integration, which has been removed from the platform.

Revision ID: 20260801_0001
Revises: 20260730_0002
Create Date: 2026-08-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_0001"
down_revision: Union[str, Sequence[str], None] = "20260730_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the broker_connections table created by 20260718_0001 and extended
    # by 20260723_0001 / 20260723_0002, then its broker_status enum type.
    op.drop_index("ix_broker_connections_user_id", table_name="broker_connections")
    op.drop_table("broker_connections")
    sa.Enum(name="broker_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Recreate the table exactly as it was defined by 20260718_0001 plus the
    # OAuth columns added by 20260723_0001 and widened by 20260723_0002.
    broker_status = sa.Enum("DISCONNECTED", "CONNECTED", name="broker_status")
    broker_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "broker_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", broker_status, nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("broker_user_id", sa.String(length=128), nullable=True),
        sa.Column("broker_metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_broker_connection_user_provider"),
    )
    op.create_index("ix_broker_connections_user_id", "broker_connections", ["user_id"], unique=False)
