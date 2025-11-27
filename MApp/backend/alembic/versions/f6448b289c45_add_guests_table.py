"""add_guests_table

Revision ID: f6448b289c45
Revises: 7cdbabc3c4cb
Create Date: 2025-11-27 17:10:01.662353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6448b289c45'
down_revision: Union[str, None] = '7cdbabc3c4cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create guests table
    op.create_table(
        'guests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('guest_name', sa.String(length=255), nullable=False),
        sa.Column('guest_email', sa.String(length=255), nullable=True),
        sa.Column('guest_phone', sa.String(length=20), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('id_type', sa.String(length=50), nullable=True),
        sa.Column('id_number', sa.String(length=100), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guests_id'), 'guests', ['id'], unique=False)
    op.create_index(op.f('ix_guests_booking_id'), 'guests', ['booking_id'], unique=False)
    op.create_foreign_key(
        'fk_guests_booking_id', 'guests', 'bookings',
        ['booking_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('fk_guests_booking_id', 'guests', type_='foreignkey')
    op.drop_index(op.f('ix_guests_booking_id'), table_name='guests')
    op.drop_index(op.f('ix_guests_id'), table_name='guests')
    op.drop_table('guests')
