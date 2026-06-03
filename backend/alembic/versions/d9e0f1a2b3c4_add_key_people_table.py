"""add_key_people_table

Revision ID: d9e0f1a2b3c4
Revises: b2c3d4e5f6a7
Create Date: 2026-06-03 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'key_people',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('linkedin_url', sa.String(), nullable=True),
        sa.Column('is_founder', sa.Boolean(), nullable=True),
        sa.Column('apollo_id', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=True,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_key_people_id', 'key_people', ['id'], unique=False)
    op.create_index('ix_key_people_company_id', 'key_people', ['company_id'], unique=False)
    op.create_index('ix_key_people_apollo_id', 'key_people', ['apollo_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_key_people_apollo_id', table_name='key_people')
    op.drop_index('ix_key_people_company_id', table_name='key_people')
    op.drop_index('ix_key_people_id', table_name='key_people')
    op.drop_table('key_people')
