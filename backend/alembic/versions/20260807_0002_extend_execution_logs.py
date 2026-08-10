"""extend execution_logs with trade details

Revision ID: 20260807_0002
Revises: 20260807_0001
Create Date: 2026-08-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260807_0002'
down_revision = '20260807_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('execution_logs', sa.Column('symbol', sa.String(100), nullable=True))
    op.add_column('execution_logs', sa.Column('side', sa.String(10), nullable=True))
    op.add_column('execution_logs', sa.Column('quantity', sa.Integer(), nullable=True))
    op.add_column('execution_logs', sa.Column('entry_price', sa.Numeric(12, 2), nullable=True))
    op.add_column('execution_logs', sa.Column('exit_price', sa.Numeric(12, 2), nullable=True))
    op.add_column('execution_logs', sa.Column('pnl', sa.Numeric(12, 2), nullable=True))
    op.add_column('execution_logs', sa.Column('exit_reason', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('execution_logs', 'exit_reason')
    op.drop_column('execution_logs', 'pnl')
    op.drop_column('execution_logs', 'exit_price')
    op.drop_column('execution_logs', 'entry_price')
    op.drop_column('execution_logs', 'quantity')
    op.drop_column('execution_logs', 'side')
    op.drop_column('execution_logs', 'symbol')
