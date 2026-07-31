"""fix users column corruption

Revision ID: 20260730_0002
Revises: 20260730_0001
Create Date: 2026-07-30 11:49:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_0002"
down_revision: Union[str, Sequence[str], None] = "20260730_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix corrupted column name in users table.
    The column appears as 'SUPER ADMIN' but should be 'full_name'.
    Also add missing columns: current_plan_id and last_login_at.
    """
    # First, try to rename the corrupted column if it exists
    # Use raw SQL to handle the edge case of spaces in column name
    conn = op.get_bind()
    
    # Check if the corrupted column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'SUPER ADMIN'
    """))
    
    if result.fetchone():
        # Rename the corrupted column
        conn.execute(sa.text('ALTER TABLE users RENAME COLUMN "SUPER ADMIN" TO full_name'))
    else:
        # Check if full_name already exists
        result = conn.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'full_name'
        """))
        
        if not result.fetchone():
            # Add full_name if it doesn't exist
            op.add_column('users', sa.Column('full_name', sa.String(length=160), nullable=True))
    
    # Check if current_plan_id exists, add if missing
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'current_plan_id'
    """))
    
    if not result.fetchone():
        op.add_column('users', sa.Column('current_plan_id', sa.Uuid(), nullable=True))
        op.create_foreign_key(
            'fk_users_current_plan_id',
            'users', 'subscription_plans',
            ['current_plan_id'], ['id'],
            ondelete='SET NULL'
        )
    
    # Check if last_login_at exists (should exist, but verify)
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'last_login_at'
    """))
    
    if not result.fetchone():
        op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """
    Revert the fix (though this shouldn't be used in practice).
    """
    # Remove columns if they were added
    conn = op.get_bind()
    
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'current_plan_id'
    """))
    
    if result.fetchone():
        op.drop_constraint('fk_users_current_plan_id', 'users', type_='foreignkey')
        op.drop_column('users', 'current_plan_id')
