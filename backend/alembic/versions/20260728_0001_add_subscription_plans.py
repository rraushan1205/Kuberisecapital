"""add subscription plans and requests

Revision ID: 20260728_0001
Revises: 20260723_0002
Create Date: 2026-07-28 18:11:40.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260728_0001'
down_revision: Union[str, None] = '20260723_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create subscription plan tier enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscription_plan_tier AS ENUM ('BASIC', 'PLUS', 'PRO', 'ELITE', 'MAX');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create subscription request status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscription_request_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create subscription_plans table
    op.execute("""
        CREATE TABLE subscription_plans (
            id UUID PRIMARY KEY,
            tier subscription_plan_tier NOT NULL UNIQUE,
            capital INTEGER NOT NULL,
            nifty_lots INTEGER NOT NULL,
            sensex_lots INTEGER NOT NULL,
            bank_nifty_lots INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index(op.f('ix_subscription_plans_tier'), 'subscription_plans', ['tier'], unique=False)
    
    # Create subscription_requests table
    op.execute("""
        CREATE TABLE subscription_requests (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
            status subscription_request_status NOT NULL DEFAULT 'PENDING',
            requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            reviewed_at TIMESTAMPTZ,
            reviewed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            notes TEXT
        )
    """)
    op.create_index(op.f('ix_subscription_requests_user_id'), 'subscription_requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscription_requests_status'), 'subscription_requests', ['status'], unique=False)
    op.create_index(op.f('ix_subscription_requests_requested_at'), 'subscription_requests', ['requested_at'], unique=False)
    
    # Add current_plan_id to users table
    op.add_column('users', sa.Column('current_plan_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_users_current_plan_id', 'users', 'subscription_plans', ['current_plan_id'], ['id'], ondelete='SET NULL')
    
    # Insert default subscription plans based on the image
    op.execute("""
        INSERT INTO subscription_plans (id, tier, capital, nifty_lots, sensex_lots, bank_nifty_lots) VALUES
        (gen_random_uuid(), 'BASIC', 60000, 2, 2, 2),
        (gen_random_uuid(), 'PLUS', 100000, 2, 2, 2),
        (gen_random_uuid(), 'PRO', 250000, 5, 5, 3),
        (gen_random_uuid(), 'ELITE', 500000, 10, 10, 5),
        (gen_random_uuid(), 'MAX', 1000000, 15, 20, 10)
    """)


def downgrade() -> None:
    op.drop_constraint('fk_users_current_plan_id', 'users', type_='foreignkey')
    op.drop_column('users', 'current_plan_id')
    
    op.drop_index(op.f('ix_subscription_requests_requested_at'), table_name='subscription_requests')
    op.drop_index(op.f('ix_subscription_requests_status'), table_name='subscription_requests')
    op.drop_index(op.f('ix_subscription_requests_user_id'), table_name='subscription_requests')
    op.drop_table('subscription_requests')
    
    op.drop_index(op.f('ix_subscription_plans_tier'), table_name='subscription_plans')
    op.drop_table('subscription_plans')
    
    op.execute('DROP TYPE subscription_request_status')
    op.execute('DROP TYPE subscription_plan_tier')
