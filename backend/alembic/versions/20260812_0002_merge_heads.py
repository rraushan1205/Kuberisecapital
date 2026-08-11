"""merge_heads

Revision ID: 20260812_0002
Revises: 1f1d58996ab5, 20260811_0001
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260812_0002'
down_revision: Union[str, Sequence[str], None] = ('1f1d58996ab5', '20260811_0001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merge-only revision: no DB changes
    pass


def downgrade() -> None:
    pass
