"""Mastery per language: language on learning_events, topic_mastery (in the key),
onboarding_records and diagnostic_responses; language_checks for re-checks

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-10-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The language a user's onboarding check ran in: the first code item they were served,
# else their profile language.
_ONBOARDING_LANGUAGE = """
    COALESCE(
        (SELECT i.language FROM diagnostic_responses r
           JOIN diagnostic_items i ON i.id = r.item_id
          WHERE r.user_id = u.id AND i.language <> 'any'
          ORDER BY r."order" LIMIT 1),
        u.preferred_language)
"""


def upgrade() -> None:
    op.add_column('onboarding_records', sa.Column('language', sa.String(10), nullable=True))
    op.execute(f"""
        UPDATE onboarding_records o SET language = {_ONBOARDING_LANGUAGE}
          FROM users u WHERE u.id = o.user_id
    """)
    user_language = """
        COALESCE((SELECT o.language FROM onboarding_records o WHERE o.user_id = t.user_id),
                 (SELECT u.preferred_language FROM users u WHERE u.id = t.user_id), 'c')
    """
    for table in ('diagnostic_responses', 'learning_events', 'topic_mastery'):
        op.add_column(table, sa.Column('language', sa.String(10), nullable=True))
        op.execute(f"UPDATE {table} t SET language = {user_language}")
        op.alter_column(table, 'language', nullable=False)

    op.drop_constraint('topic_mastery_pkey', 'topic_mastery', type_='primary')
    op.create_primary_key('topic_mastery_pkey', 'topic_mastery',
                          ['user_id', 'topic', 'language'])

    op.create_table(
        'language_checks',
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('language', sa.String(10), primary_key=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('diagnostic_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_item_id', sa.Integer(),
                  sa.ForeignKey('diagnostic_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('seeds', sa.JSON(), nullable=True),
        sa.Column('title', sa.String(80), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('language_checks')
    op.execute("""
        DELETE FROM topic_mastery t USING onboarding_records o
         WHERE o.user_id = t.user_id AND t.language <> o.language
    """)
    op.drop_constraint('topic_mastery_pkey', 'topic_mastery', type_='primary')
    op.create_primary_key('topic_mastery_pkey', 'topic_mastery', ['user_id', 'topic'])
    for table in ('topic_mastery', 'learning_events', 'diagnostic_responses',
                  'onboarding_records'):
        op.drop_column(table, 'language')
