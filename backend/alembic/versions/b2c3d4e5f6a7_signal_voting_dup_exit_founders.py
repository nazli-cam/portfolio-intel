"""signal_voting_dup_exit_founders

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-03 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Signal voting + duplicate fields ---
    op.add_column('signals', sa.Column('is_accurate', sa.Boolean(), nullable=True))
    op.add_column('signals', sa.Column('is_duplicate', sa.Boolean(), nullable=True))

    # --- EXIT enum value (PostgreSQL native enum needs ALTER TYPE) ---
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE signaltype ADD VALUE IF NOT EXISTS 'exit'")

    # --- Founders table ---
    op.create_table(
        'founders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('linkedin_url', sa.String(), nullable=True),
        sa.Column('twitter_url', sa.String(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_founders_id', 'founders', ['id'], unique=False)
    op.create_index('ix_founders_name', 'founders', ['name'], unique=False)
    op.create_index('ix_founders_company_id', 'founders', ['company_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_founders_company_id', table_name='founders')
    op.drop_index('ix_founders_name', table_name='founders')
    op.drop_index('ix_founders_id', table_name='founders')
    op.drop_table('founders')
    op.drop_column('signals', 'is_duplicate')
    op.drop_column('signals', 'is_accurate')
