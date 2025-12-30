"""create notifications

Revision ID: 005_create_notifications
Revises: 004_create_subscriptions
Create Date: 2025-12-30 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_create_notifications'
down_revision: Union[str, None] = '004_create_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types explicitly
    op.execute("CREATE TYPE notification_channel AS ENUM ('EMAIL', 'SMS', 'IN_APP', 'PUSH')")
    op.execute("CREATE TYPE notification_status AS ENUM ('PENDING', 'SENT', 'FAILED', 'READ')")
    
    notification_channel = postgresql.ENUM('EMAIL', 'SMS', 'IN_APP', 'PUSH', name='notification_channel', create_type=False)
    notification_status = postgresql.ENUM('PENDING', 'SENT', 'FAILED', 'READ', name='notification_status', create_type=False)
    
    # Create notification_templates table
    op.create_table(
        'notification_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_key', sa.String(length=100), nullable=False),
        sa.Column('channel', notification_channel, nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_key', 'channel', name='uq_template_key_channel')
    )
    op.create_index('idx_template_key', 'notification_templates', ['template_key'])
    op.create_index('idx_template_channel', 'notification_templates', ['channel'])
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('channel', notification_channel, nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('notification_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', notification_status, server_default='PENDING', nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['notification_templates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('idx_notifications_status', 'notifications', ['status'])
    op.create_index('idx_notifications_scheduled_at', 'notifications', ['scheduled_at'])
    op.create_index('idx_notifications_channel', 'notifications', ['channel'])
    
    # Create user_notification_preferences table
    op.create_table(
        'user_notification_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), server_default='true'),
        sa.Column('sms_enabled', sa.Boolean(), server_default='true'),
        sa.Column('push_enabled', sa.Boolean(), server_default='true'),
        sa.Column('subscription_alerts', sa.Boolean(), server_default='true'),
        sa.Column('booking_alerts', sa.Boolean(), server_default='true'),
        sa.Column('marketing_emails', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('idx_user_prefs_user_id', 'user_notification_preferences', ['user_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('idx_user_prefs_user_id', 'user_notification_preferences')
    op.drop_table('user_notification_preferences')
    
    op.drop_index('idx_notifications_channel', 'notifications')
    op.drop_index('idx_notifications_scheduled_at', 'notifications')
    op.drop_index('idx_notifications_status', 'notifications')
    op.drop_index('idx_notifications_user_id', 'notifications')
    op.drop_table('notifications')
    
    op.drop_index('idx_template_channel', 'notification_templates')
    op.drop_index('idx_template_key', 'notification_templates')
    op.drop_table('notification_templates')
    
    # Drop enum types
    notification_status = postgresql.ENUM('PENDING', 'SENT', 'FAILED', 'READ', name='notification_status')
    notification_channel = postgresql.ENUM('EMAIL', 'SMS', 'IN_APP', 'PUSH', name='notification_channel')
    
    notification_status.drop(op.get_bind(), checkfirst=True)
    notification_channel.drop(op.get_bind(), checkfirst=True)
