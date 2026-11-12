"""gamification_awards: the award ledger, one row per points/level_up/badge

Revision ID: f6a1b2c3d4e5
Revises: f3c2a7e9b104
Create Date: 2026-10-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f6a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'f3c2a7e9b104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'gamification_awards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('learning_event_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=12), nullable=False),
        sa.Column('code', sa.String(length=40), nullable=False),
        sa.Column('dedupe_key', sa.String(length=80), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('message', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['learning_event_id'], ['learning_events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'dedupe_key', name='uq_award_user_key'),
    )
    op.create_index(op.f('ix_gamification_awards_id'), 'gamification_awards', ['id'])
    op.create_index(op.f('ix_gamification_awards_user_id'), 'gamification_awards', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_gamification_awards_user_id'), table_name='gamification_awards')
    op.drop_index(op.f('ix_gamification_awards_id'), table_name='gamification_awards')
    op.drop_table('gamification_awards')
