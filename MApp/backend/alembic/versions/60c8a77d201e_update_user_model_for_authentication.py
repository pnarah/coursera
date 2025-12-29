"""update_user_model_for_authentication

Revision ID: 60c8a77d201e
Revises: c4c726567d9d
Create Date: 2025-12-29 21:17:47.861586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60c8a77d201e'
down_revision: Union[str, None] = 'c4c726567d9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update user role enum to include new roles
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('GUEST', 'HOTEL_EMPLOYEE', 'VENDOR_ADMIN', 'SYSTEM_ADMIN')")
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole 
        USING CASE 
            WHEN role::text = 'guest' THEN 'GUEST'::userrole
            WHEN role::text = 'admin' THEN 'SYSTEM_ADMIN'::userrole
            WHEN role::text = 'staff' THEN 'HOTEL_EMPLOYEE'::userrole
            ELSE 'GUEST'::userrole
        END
    """)
    op.execute("DROP TYPE userrole_old")
    
    # Add hotel_id column
    op.add_column('users', sa.Column('hotel_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_hotel_id', 'users', 'hotels', ['hotel_id'], ['id'])
    op.create_index('ix_users_hotel_id', 'users', ['hotel_id'])
    
    # Add last_login column
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove last_login column
    op.drop_column('users', 'last_login')
    
    # Remove hotel_id column and constraints
    op.drop_index('ix_users_hotel_id', 'users')
    op.drop_constraint('fk_users_hotel_id', 'users', type_='foreignkey')
    op.drop_column('users', 'hotel_id')
    
    # Revert user role enum
    op.execute("ALTER TYPE userrole RENAME TO userrole_new")
    op.execute("CREATE TYPE userrole AS ENUM ('guest', 'admin', 'staff')")
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole 
        USING CASE 
            WHEN role::text = 'GUEST' THEN 'guest'::userrole
            WHEN role::text = 'SYSTEM_ADMIN' THEN 'admin'::userrole
            WHEN role::text = 'HOTEL_EMPLOYEE' THEN 'staff'::userrole
            WHEN role::text = 'VENDOR_ADMIN' THEN 'admin'::userrole
            ELSE 'guest'::userrole
        END
    """)
    op.execute("DROP TYPE userrole_new")
