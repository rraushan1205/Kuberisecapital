"""widen broker token columns

Revision ID: 20260723_0002
Revises: 20260723_0001
Create Date: 2026-07-23 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260723_0002'
down_revision = '20260723_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen encrypted token columns — String(512) was too small for real
    # encrypted Fyers OAuth tokens (Bug 7)
    op.alter_column(
        'broker_connections', 'access_token_encrypted',
        existing_type=sa.String(512),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        'broker_connections', 'refresh_token_encrypted',
        existing_type=sa.String(512),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'broker_connections', 'refresh_token_encrypted',
        existing_type=sa.Text(),
        type_=sa.String(512),
        existing_nullable=True,
    )
    op.alter_column(
        'broker_connections', 'access_token_encrypted',
        existing_type=sa.Text(),
        type_=sa.String(512),
        existing_nullable=True,
    )
