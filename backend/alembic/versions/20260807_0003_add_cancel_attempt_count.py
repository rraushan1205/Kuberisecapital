"""add cancel_attempt_count to strategy_state

Revision ID: 20260807_0003
Revises: 20260807_0002
Create Date: 2026-08-07 17:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260807_0003'
down_revision = '20260807_0002'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add cancel_attempt_count column to strategy_state table.
    
    This column tracks cross-tick retry attempts for cancelling TP/SL orders
    that fail to cancel after a position is filled. Prevents infinite retry loops
    by limiting total cancel attempts across multiple monitor ticks.
    """
    op.add_column('strategy_state', sa.Column('cancel_attempt_count', sa.Integer(), nullable=True, server_default='0'))
    
    # Update existing rows to have default value
    op.execute("UPDATE strategy_state SET cancel_attempt_count = 0 WHERE cancel_attempt_count IS NULL")
    
    # Make column non-nullable after setting defaults
    op.alter_column('strategy_state', 'cancel_attempt_count', nullable=False)


def downgrade():
    """Remove cancel_attempt_count column"""
    op.drop_column('strategy_state', 'cancel_attempt_count')
