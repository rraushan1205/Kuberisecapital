"""add broker oauth fields

Revision ID: 20260723_0001
Revises: 20260718_0001
Create Date: 2026-07-23 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260723_0001'
down_revision = '20260718_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add OAuth credential fields to broker_connections table
    op.add_column('broker_connections', sa.Column('access_token_encrypted', sa.String(512), nullable=True))
    op.add_column('broker_connections', sa.Column('refresh_token_encrypted', sa.String(512), nullable=True))
    op.add_column('broker_connections', sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('broker_connections', sa.Column('broker_user_id', sa.String(128), nullable=True))
    op.add_column('broker_connections', sa.Column('broker_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove OAuth credential fields
    op.drop_column('broker_connections', 'broker_metadata')
    op.drop_column('broker_connections', 'broker_user_id')
    op.drop_column('broker_connections', 'token_expires_at')
    op.drop_column('broker_connections', 'refresh_token_encrypted')
    op.drop_column('broker_connections', 'access_token_encrypted')
