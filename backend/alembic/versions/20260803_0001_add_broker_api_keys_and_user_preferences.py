"""add broker api keys and user preferences

Revision ID: 20260803_0001
Revises: 20260730_0002
Create Date: 2026-08-03 13:47:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260803_0001"
down_revision: Union[str, Sequence[str], None] = "20260730_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add broker API key storage and user broker preferences.
    
    Changes:
    1. Create login_method enum type
    2. Add login_method column to users table
    3. Add last_broker_used column to users table
    4. Create broker_api_keys table
    """
    # Create login_method enum type if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE login_method AS ENUM ('OAUTH', 'API_KEY');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add new columns to users table
    op.add_column('users', sa.Column('login_method', sa.Enum('OAUTH', 'API_KEY', name='login_method'), nullable=True))
    op.add_column('users', sa.Column('last_broker_used', sa.String(length=64), nullable=True))
    
    # Create broker_api_keys table
    op.create_table(
        'broker_api_keys',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('api_secret_encrypted', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_broker_api_key_user_provider')
    )
    
    # Create indexes
    op.create_index(op.f('ix_broker_api_keys_user_id'), 'broker_api_keys', ['user_id'], unique=False)
    op.create_index(op.f('ix_broker_api_keys_provider'), 'broker_api_keys', ['provider'], unique=False)


def downgrade() -> None:
    """
    Revert broker API key storage and user broker preferences.
    """
    # Drop indexes
    op.drop_index(op.f('ix_broker_api_keys_provider'), table_name='broker_api_keys')
    op.drop_index(op.f('ix_broker_api_keys_user_id'), table_name='broker_api_keys')
    
    # Drop broker_api_keys table
    op.drop_table('broker_api_keys')
    
    # Drop columns from users table
    op.drop_column('users', 'last_broker_used')
    op.drop_column('users', 'login_method')
    
    # Drop login_method enum type
    op.execute("DROP TYPE login_method")
