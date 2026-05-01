"""add user_profiles and eligibility_history tables

Revision ID: a3f8b2c1d4e5
Revises: eb0746cbeaa3
Create Date: 2026-05-01 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8b2c1d4e5'
down_revision: Union[str, None] = 'eb0746cbeaa3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update schemes.name column length from 300 to 500
    op.alter_column('schemes', 'name',
        existing_type=sa.String(length=300),
        type_=sa.String(length=500),
        existing_nullable=False,
    )

    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('annual_income', sa.Float(), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('caste_category', sa.String(length=20), nullable=True),
        sa.Column('occupation', sa.String(length=50), nullable=True),
        sa.Column('is_disabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_minority', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_bpl', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_student', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_senior_citizen', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('land_owned_acres', sa.Float(), nullable=True),
        sa.Column('num_children', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)

    # Create eligibility_history table
    op.create_table('eligibility_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('profile_snapshot', sa.Text(), nullable=False),
        sa.Column('results_snapshot', sa.Text(), nullable=False),
        sa.Column('total_matched', sa.Integer(), nullable=False),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_eligibility_history_id'), 'eligibility_history', ['id'], unique=False)
    op.create_index(op.f('ix_eligibility_history_user_id'), 'eligibility_history', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_eligibility_history_user_id'), table_name='eligibility_history')
    op.drop_index(op.f('ix_eligibility_history_id'), table_name='eligibility_history')
    op.drop_table('eligibility_history')
    op.drop_index(op.f('ix_user_profiles_id'), table_name='user_profiles')
    op.drop_table('user_profiles')

    # Revert schemes.name column length
    op.alter_column('schemes', 'name',
        existing_type=sa.String(length=500),
        type_=sa.String(length=300),
        existing_nullable=False,
    )
