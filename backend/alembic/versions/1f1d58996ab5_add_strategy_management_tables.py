"""add_strategy_management_tables

Revision ID: 1f1d58996ab5
Revises: 20260807_0003
Create Date: 2026-08-07 18:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1f1d58996ab5'
down_revision: Union[str, None] = '20260807_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create strategy_definitions table
    op.create_table(
        'strategy_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('config_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_strategy_definitions_is_active'), 'strategy_definitions', ['is_active'], unique=False)
    
    # Create user_strategy_permissions table
    op.create_table(
        'user_strategy_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allow_admin_trading', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('max_daily_loss', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_position_size', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_strategy_permissions_user_id'), 'user_strategy_permissions', ['user_id'], unique=True)
    
    # Create user_strategy_assignments table
    op.create_table(
        'user_strategy_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_def_id', sa.Integer(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('stopped_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['strategy_def_id'], ['strategy_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'strategy_def_id', name='uq_user_strategy_assignment')
    )
    op.create_index(op.f('ix_user_strategy_assignments_user_id'), 'user_strategy_assignments', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_strategy_assignments_is_active'), 'user_strategy_assignments', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_strategy_assignments_is_active'), table_name='user_strategy_assignments')
    op.drop_index(op.f('ix_user_strategy_assignments_user_id'), table_name='user_strategy_assignments')
    op.drop_table('user_strategy_assignments')
    
    op.drop_index(op.f('ix_user_strategy_permissions_user_id'), table_name='user_strategy_permissions')
    op.drop_table('user_strategy_permissions')
    
    op.drop_index(op.f('ix_strategy_definitions_is_active'), table_name='strategy_definitions')
    op.drop_table('strategy_definitions')
