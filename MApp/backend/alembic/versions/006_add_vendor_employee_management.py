"""add vendor employee management

Revision ID: 006_vendor_employee_mgmt
Revises: 005_create_notifications
Create Date: 2025-12-30 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_vendor_employee_mgmt'
down_revision: Union[str, None] = '005_create_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE employee_role AS ENUM ('MANAGER', 'RECEPTIONIST', 'HOUSEKEEPING', 'MAINTENANCE')")
    op.execute("CREATE TYPE approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED')")
    
    employee_role = postgresql.ENUM('MANAGER', 'RECEPTIONIST', 'HOUSEKEEPING', 'MAINTENANCE', name='employee_role', create_type=False)
    approval_status = postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='approval_status', create_type=False)
    
    # Add vendor-specific fields to users table
    op.add_column('users', sa.Column('vendor_approved', sa.Boolean(), server_default='false'))
    op.add_column('users', sa.Column('approval_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('approved_by', sa.Integer(), nullable=True))
    
    # Add foreign key for approved_by
    op.create_foreign_key(
        'fk_users_approved_by',
        'users', 'users',
        ['approved_by'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create vendor_approval_requests table
    op.create_table(
        'vendor_approval_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('business_name', sa.String(length=255), nullable=False),
        sa.Column('business_address', sa.Text(), nullable=True),
        sa.Column('tax_id', sa.String(length=50), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=15), nullable=True),
        sa.Column('status', approval_status, server_default='PENDING', nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vendor_requests_status', 'vendor_approval_requests', ['status'])
    op.create_index('idx_vendor_requests_user_id', 'vendor_approval_requests', ['user_id'])
    
    # Create employee_invitations table
    op.create_table(
        'employee_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hotel_id', sa.Integer(), nullable=False),
        sa.Column('mobile_number', sa.String(length=15), nullable=False),
        sa.Column('role', employee_role, nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('invited_by', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=100), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index('idx_employee_invitations_token', 'employee_invitations', ['token'])
    op.create_index('idx_employee_invitations_hotel_id', 'employee_invitations', ['hotel_id'])
    
    # Create hotel_employees table
    op.create_table(
        'hotel_employees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('hotel_id', sa.Integer(), nullable=False),
        sa.Column('role', employee_role, nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('invited_by', sa.Integer(), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'hotel_id', name='uq_user_hotel')
    )
    op.create_index('idx_hotel_employees_hotel_id', 'hotel_employees', ['hotel_id'])
    op.create_index('idx_hotel_employees_user_id', 'hotel_employees', ['user_id'])
    op.create_index('idx_hotel_employees_is_active', 'hotel_employees', ['is_active'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('idx_hotel_employees_is_active', 'hotel_employees')
    op.drop_index('idx_hotel_employees_user_id', 'hotel_employees')
    op.drop_index('idx_hotel_employees_hotel_id', 'hotel_employees')
    op.drop_table('hotel_employees')
    
    op.drop_index('idx_employee_invitations_hotel_id', 'employee_invitations')
    op.drop_index('idx_employee_invitations_token', 'employee_invitations')
    op.drop_table('employee_invitations')
    
    op.drop_index('idx_vendor_requests_user_id', 'vendor_approval_requests')
    op.drop_index('idx_vendor_requests_status', 'vendor_approval_requests')
    op.drop_table('vendor_approval_requests')
    
    # Drop vendor fields from users table
    op.drop_constraint('fk_users_approved_by', 'users', type_='foreignkey')
    op.drop_column('users', 'approved_by')
    op.drop_column('users', 'approval_date')
    op.drop_column('users', 'vendor_approved')
    
    # Drop enum types
    op.execute('DROP TYPE approval_status')
    op.execute('DROP TYPE employee_role')
