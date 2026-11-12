"""practice_sessions: bounded Practice sessions, and session_id on learning_events
and hint_events

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-10-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EVENT_TABLES = ('learning_events', 'hint_events')


def upgrade() -> None:
    op.create_table(
        'practice_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_reason', sa.String(length=16), nullable=True),
        sa.Column('graded_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('served', sa.JSON(), nullable=False),
        sa.Column('wrap_up_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('feedback', sa.JSON(), nullable=True),
        sa.Column('feedback_status', sa.String(length=12), server_default='none',
                  nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_practice_sessions_id'), 'practice_sessions', ['id'])
    op.create_index(op.f('ix_practice_sessions_user_id'), 'practice_sessions', ['user_id'])

    for table in _EVENT_TABLES:
        op.add_column(table, sa.Column('session_id', sa.Integer(), nullable=True))
        op.create_foreign_key(f'{table}_session_id_fkey', table, 'practice_sessions',
                              ['session_id'], ['id'], ondelete='SET NULL')
        op.create_index(op.f(f'ix_{table}_session_id'), table, ['session_id'])


def downgrade() -> None:
    for table in _EVENT_TABLES:
        op.drop_index(op.f(f'ix_{table}_session_id'), table_name=table)
        op.drop_constraint(f'{table}_session_id_fkey', table, type_='foreignkey')
        op.drop_column(table, 'session_id')
    op.drop_index(op.f('ix_practice_sessions_user_id'), table_name='practice_sessions')
    op.drop_index(op.f('ix_practice_sessions_id'), table_name='practice_sessions')
    op.drop_table('practice_sessions')
