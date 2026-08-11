"""add auth token tables

Revision ID: 20260812_0001
Revises: 20260811_0001
Create Date: 2026-08-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260812_0001'
down_revision = '20260811_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_verification_tokens',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('token_hash', sa.String(512), nullable=False, unique=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('token_hash', sa.String(512), nullable=False, unique=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('password_reset_tokens')
    op.drop_table('email_verification_tokens')
