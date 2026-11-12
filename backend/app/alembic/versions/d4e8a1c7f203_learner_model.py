"""learner model: events, topic mastery, hints, MCQ and debug banks

Revision ID: d4e8a1c7f203
Revises: b2f7d41c9a83
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e8a1c7f203'
down_revision: Union[str, Sequence[str], None] = 'b2f7d41c9a83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen copy of the bank-tag mapping at the time of this migration, so later edits
# to app.core.topics cannot change what this revision did.
_BANK_TOPICS = {
    "arithmetic": "basics_io",
    "numbers": "basics_io",
    "sets": "hashing_sets",
    "hashing": "hashing_sets",
    "two pointers": "arrays",
    "stacks": "stacks_queues",
    "dynamic programming": "dynamic_programming",
}


def _timestamp():
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        'learning_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('topic', sa.String(40), nullable=True),
        sa.Column('raw_topic', sa.String(100), nullable=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('hint_level_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('misconceptions', sa.JSON(), nullable=True),
        sa.Column('mastery_before', sa.Float(), nullable=True),
        sa.Column('mastery_after', sa.Float(), nullable=True),
        sa.Column('source_ref', sa.String(60), nullable=True),
        sa.Column('created_at', _timestamp(), server_default=sa.func.now()),
    )
    op.create_index('ix_learning_events_id', 'learning_events', ['id'])
    op.create_index('ix_learning_events_user_id', 'learning_events', ['user_id'])
    op.create_index('ix_learning_events_topic', 'learning_events', ['topic'])
    op.create_index('ix_learning_events_created_at', 'learning_events', ['created_at'])

    op.create_table(
        'topic_mastery',
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('topic', sa.String(40), primary_key=True),
        sa.Column('mastery', sa.Float(), nullable=False),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_event_at', _timestamp(), nullable=True),
    )

    op.create_table(
        'hint_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', sa.Integer(),
                  sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evaluation_id', sa.Integer(),
                  sa.ForeignKey('code_evaluations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('was_blocked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', _timestamp(), server_default=sa.func.now()),
    )
    op.create_index('ix_hint_events_id', 'hint_events', ['id'])
    op.create_index('ix_hint_events_user_id', 'hint_events', ['user_id'])
    op.create_index('ix_hint_events_problem_id', 'hint_events', ['problem_id'])

    op.create_table(
        'mcq_questions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_id', sa.String(60), nullable=False, unique=True),
        sa.Column('topic', sa.String(40), nullable=False),
        sa.Column('difficulty', sa.String(10), nullable=False),
        sa.Column('stem', sa.Text(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('answer_index', sa.Integer(), nullable=False),
        sa.Column('explanations', sa.JSON(), nullable=True),
        sa.Column('is_diagnostic', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('reviewed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', _timestamp(), server_default=sa.func.now()),
    )
    op.create_index('ix_mcq_questions_id', 'mcq_questions', ['id'])
    op.create_index('ix_mcq_questions_topic', 'mcq_questions', ['topic'])

    op.create_table(
        'mcq_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.Integer(),
                  sa.ForeignKey('mcq_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chosen_index', sa.Integer(), nullable=False),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('created_at', _timestamp(), server_default=sa.func.now()),
    )
    op.create_index('ix_mcq_attempts_id', 'mcq_attempts', ['id'])
    op.create_index('ix_mcq_attempts_user_id', 'mcq_attempts', ['user_id'])

    op.create_table(
        'debug_challenges',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_id', sa.String(60), nullable=False, unique=True),
        sa.Column('problem_id', sa.Integer(),
                  sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic', sa.String(40), nullable=False),
        sa.Column('difficulty', sa.String(10), nullable=False),
        sa.Column('language', sa.String(20), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('buggy_code', sa.Text(), nullable=False),
        sa.Column('fixed_code', sa.Text(), nullable=False),
        sa.Column('bug_type', sa.String(40), nullable=False),
        sa.Column('reviewed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', _timestamp(), server_default=sa.func.now()),
    )
    op.create_index('ix_debug_challenges_id', 'debug_challenges', ['id'])
    op.create_index('ix_debug_challenges_topic', 'debug_challenges', ['topic'])

    op.create_table(
        'debug_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('challenge_id', sa.Integer(),
                  sa.ForeignKey('debug_challenges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('submitted_code', sa.Text(), nullable=False),
        sa.Column('tests_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tests_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fixed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', _timestamp(), server_default=sa.func.now()),
    )
    op.create_index('ix_debug_attempts_id', 'debug_attempts', ['id'])
    op.create_index('ix_debug_attempts_user_id', 'debug_attempts', ['user_id'])

    problems = sa.table('problems', sa.column('topic', sa.String))
    for old, new in _BANK_TOPICS.items():
        op.execute(
            problems.update()
            .where(sa.func.lower(problems.c.topic) == old)
            .values(topic=new)
        )


def downgrade() -> None:
    # The topic rename is not reversed: several bank tags collapsed into one id, so
    # the original tag cannot be recovered, and the canonical ids stay valid.
    op.drop_table('debug_attempts')
    op.drop_table('debug_challenges')
    op.drop_table('mcq_attempts')
    op.drop_table('mcq_questions')
    op.drop_table('hint_events')
    op.drop_table('topic_mastery')
    op.drop_table('learning_events')
