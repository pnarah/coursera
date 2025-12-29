"""add_rbac_permissions_and_audit_log

Revision ID: 093c3d61f467
Revises: 60c8a77d201e
Create Date: 2025-12-29 21:43:12.139765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '093c3d61f467'
down_revision: Union[str, None] = '60c8a77d201e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create hotel_employee_permissions table
    op.create_table(
        'hotel_employee_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('permission', sa.String(length=100), nullable=False),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_hotel_employee_permissions_user_id', 'hotel_employee_permissions', ['user_id'])
    op.create_index('idx_hotel_employee_permissions_permission', 'hotel_employee_permissions', ['permission'])
    
    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_action', 'audit_log', ['action'])
    op.create_index('idx_audit_log_resource', 'audit_log', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_log_created_at', 'audit_log', ['created_at'])
    
    # Add new columns to users table
    op.add_column('users', sa.Column('created_by', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False))
    
    # Add foreign key for created_by
    op.create_foreign_key('fk_users_created_by', 'users', 'users', ['created_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # Drop foreign key and columns from users table
    op.drop_constraint('fk_users_created_by', 'users', type_='foreignkey')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'created_by')
    
    # Drop audit_log table
    op.drop_index('idx_audit_log_created_at', 'audit_log')
    op.drop_index('idx_audit_log_resource', 'audit_log')
    op.drop_index('idx_audit_log_action', 'audit_log')
    op.drop_index('idx_audit_log_user_id', 'audit_log')
    op.drop_table('audit_log')
    
    # Drop hotel_employee_permissions table
    op.drop_index('idx_hotel_employee_permissions_permission', 'hotel_employee_permissions')
    op.drop_index('idx_hotel_employee_permissions_user_id', 'hotel_employee_permissions')
    op.drop_table('hotel_employee_permissions')
