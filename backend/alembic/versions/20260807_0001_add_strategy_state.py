"""add strategy_state table

Revision ID: 20260807_0001
Revises: 20260803_0001
Create Date: 2026-08-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260807_0001'
down_revision = '20260803_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'strategy_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('broker', sa.String(50), nullable=False),
        
        # Signal tracking
        sa.Column('last_signal_candle', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_signal_type', sa.String(20), nullable=True),  # BUY_CE, BUY_PE, SELL
        
        # Position tracking
        sa.Column('has_open_position', sa.Boolean(), default=False),
        sa.Column('position_symbol', sa.String(100), nullable=True),
        sa.Column('position_side', sa.String(10), nullable=True),  # BUY, SELL
        sa.Column('position_qty', sa.Integer(), nullable=True),
        sa.Column('position_entry_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('position_entry_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('entry_order_id', sa.String(100), nullable=True),
        
        # TP/SL tracking
        sa.Column('tp_order_id', sa.String(100), nullable=True),
        sa.Column('sl_order_id', sa.String(100), nullable=True),
        sa.Column('target_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('stoploss_price', sa.Numeric(12, 2), nullable=True),
        
        # Metadata
        sa.Column('status', sa.String(20), default='idle'),  # idle, running, stopped, error
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'strategy_id', name='uq_user_strategy')
    )
    
    op.create_index('ix_strategy_state_user_id', 'strategy_state', ['user_id'])
    op.create_index('ix_strategy_state_status', 'strategy_state', ['status'])


def downgrade():
    op.drop_index('ix_strategy_state_status', table_name='strategy_state')
    op.drop_index('ix_strategy_state_user_id', table_name='strategy_state')
    op.drop_table('strategy_state')
