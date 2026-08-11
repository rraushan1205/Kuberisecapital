"""add_totp_2fa_fields

Revision ID: 20260811_0001
Revises: 20260807_0003_add_cancel_attempt_count
Create Date: 2026-08-11 06:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260811_0001'
down_revision: Union[str, None] = '20260807_0003_add_cancel_attempt_count'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('users', sa.Column('totp_secret', sa.String(length=256), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), server_default='false', nullable=False))

def downgrade() -> None:
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')