"""llm_calls: one row per LLM gateway call

Revision ID: f1a0b7c3d921
Revises: e5a2c9b3d418
Create Date: 2026-10-11 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f1a0b7c3d921'
down_revision: Union[str, Sequence[str], None] = 'e5a2c9b3d418'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purpose', sa.String(length=30), nullable=False),
        sa.Column('key_slot', sa.Integer(), nullable=True),
        sa.Column('model', sa.String(length=120), nullable=False),
        sa.Column('queued_ms', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False),
        sa.Column('tokens_out', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_llm_calls_id'), 'llm_calls', ['id'])
    op.create_index(op.f('ix_llm_calls_purpose'), 'llm_calls', ['purpose'])
    op.create_index(op.f('ix_llm_calls_user_id'), 'llm_calls', ['user_id'])
    op.create_index(op.f('ix_llm_calls_created_at'), 'llm_calls', ['created_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_llm_calls_created_at'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_user_id'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_purpose'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_id'), table_name='llm_calls')
    op.drop_table('llm_calls')
