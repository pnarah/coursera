"""add admin features

Revision ID: 007_admin_features
Revises: 006_vendor_employee_mgmt
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_admin_features'
down_revision: Union[str, None] = '006_vendor_employee_mgmt'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create admin_audit_log table
    op.create_table(
        'admin_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_audit_log_admin_user_id', 'admin_audit_log', ['admin_user_id'])
    op.create_index('ix_admin_audit_log_action', 'admin_audit_log', ['action'])
    op.create_index('ix_admin_audit_log_resource_type', 'admin_audit_log', ['resource_type'])
    op.create_index('ix_admin_audit_log_created_at', 'admin_audit_log', ['created_at'])

    # Create system_config table
    op.create_table(
        'system_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(100), nullable=False, unique=True),
        sa.Column('config_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_editable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_system_config_config_key', 'system_config', ['config_key'], unique=True)

    # Create platform_metrics table
    op.create_table(
        'platform_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_key', sa.String(100), nullable=False, unique=True),
        sa.Column('metric_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('calculated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_metrics_metric_key', 'platform_metrics', ['metric_key'], unique=True)
    op.create_index('ix_platform_metrics_calculated_at', 'platform_metrics', ['calculated_at'])


def downgrade() -> None:
    op.drop_index('ix_platform_metrics_calculated_at', table_name='platform_metrics')
    op.drop_index('ix_platform_metrics_metric_key', table_name='platform_metrics')
    op.drop_table('platform_metrics')
    
    op.drop_index('ix_system_config_config_key', table_name='system_config')
    op.drop_table('system_config')
    
    op.drop_index('ix_admin_audit_log_created_at', table_name='admin_audit_log')
    op.drop_index('ix_admin_audit_log_resource_type', table_name='admin_audit_log')
    op.drop_index('ix_admin_audit_log_action', table_name='admin_audit_log')
    op.drop_index('ix_admin_audit_log_admin_user_id', table_name='admin_audit_log')
    op.drop_table('admin_audit_log')
