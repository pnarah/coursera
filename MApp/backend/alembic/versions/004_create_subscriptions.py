"""create subscriptions

Revision ID: 004_create_subscriptions
Revises: 093c3d61f467
Create Date: 2025-12-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_create_subscriptions'
down_revision: Union[str, None] = '0750195d594f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create subscription_plans table
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('duration_months', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD'),
        sa.Column('max_rooms', sa.Integer(), nullable=True),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('discount_percentage', sa.Numeric(5, 2), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )

    # Create vendor_subscriptions table
    op.create_table(
        'vendor_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('hotel_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('plan_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('grace_period_end', sa.Date(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), server_default='false'),
        sa.Column('payment_method_id', sa.Integer(), nullable=True),
        sa.Column('next_billing_date', sa.Date(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['vendor_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hotel_id', 'start_date', name='uq_hotel_start_date')
    )
    op.create_index('idx_subscriptions_vendor', 'vendor_subscriptions', ['vendor_id'])
    op.create_index('idx_subscriptions_hotel', 'vendor_subscriptions', ['hotel_id'])
    op.create_index('idx_subscriptions_status', 'vendor_subscriptions', ['status'])
    op.create_index('idx_subscriptions_end_date', 'vendor_subscriptions', ['end_date'])

    # Create subscription_payments table
    op.create_table(
        'subscription_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD'),
        sa.Column('payment_date', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('transaction_id', sa.String(length=255), nullable=True),
        sa.Column('payment_gateway', sa.String(length=50), nullable=True),
        sa.Column('gateway_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['subscription_id'], ['vendor_subscriptions.id']),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    op.create_index('idx_payments_subscription', 'subscription_payments', ['subscription_id'])
    op.create_index('idx_payments_status', 'subscription_payments', ['status'])
    op.create_index('idx_payments_transaction', 'subscription_payments', ['transaction_id'])

    # Create subscription_notifications table
    op.create_table(
        'subscription_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('recipient_user_id', sa.Integer(), nullable=True),
        sa.Column('channels', postgresql.ARRAY(sa.String(length=50)), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['subscription_id'], ['vendor_subscriptions.id']),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notifications_subscription', 'subscription_notifications', ['subscription_id'])
    op.create_index('idx_notifications_sent', 'subscription_notifications', ['sent_at'])

    # Add subscription column to hotels table (just the flag, not FK)
    op.add_column('hotels', sa.Column('is_subscription_active', sa.Boolean(), server_default='false'))


def downgrade() -> None:
    # Remove columns from hotels table
    op.drop_column('hotels', 'is_subscription_active')

    # Drop subscription_notifications table
    op.drop_index('idx_notifications_sent', 'subscription_notifications')
    op.drop_index('idx_notifications_subscription', 'subscription_notifications')
    op.drop_table('subscription_notifications')

    # Drop subscription_payments table
    op.drop_index('idx_payments_transaction', 'subscription_payments')
    op.drop_index('idx_payments_status', 'subscription_payments')
    op.drop_index('idx_payments_subscription', 'subscription_payments')
    op.drop_table('subscription_payments')

    # Drop vendor_subscriptions table
    op.drop_index('idx_subscriptions_end_date', 'vendor_subscriptions')
    op.drop_index('idx_subscriptions_status', 'vendor_subscriptions')
    op.drop_index('idx_subscriptions_hotel', 'vendor_subscriptions')
    op.drop_index('idx_subscriptions_vendor', 'vendor_subscriptions')
    op.drop_table('vendor_subscriptions')

    # Drop subscription_plans table
    op.drop_table('subscription_plans')
