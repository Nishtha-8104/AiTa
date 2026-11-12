"""topic practice: theory_questions, theory_attempts, and topic runs on practice_sessions

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-10-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e0f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'theory_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=60), nullable=False),
        sa.Column('topic', sa.String(length=40), nullable=False),
        sa.Column('difficulty', sa.String(length=10), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('model_answer', sa.Text(), nullable=False),
        sa.Column('key_points', sa.JSON(), nullable=False),
        sa.Column('reviewed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )
    op.create_index(op.f('ix_theory_questions_id'), 'theory_questions', ['id'])
    op.create_index(op.f('ix_theory_questions_topic'), 'theory_questions', ['topic'])
    op.create_table(
        'theory_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('points_present', sa.JSON(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['theory_questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_theory_attempts_id'), 'theory_attempts', ['id'])
    op.create_index(op.f('ix_theory_attempts_user_id'), 'theory_attempts', ['user_id'])
    op.add_column('practice_sessions', sa.Column('topic', sa.String(length=40), nullable=True))
    op.add_column('practice_sessions', sa.Column('plan', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('practice_sessions', 'plan')
    op.drop_column('practice_sessions', 'topic')
    op.drop_index(op.f('ix_theory_attempts_user_id'), table_name='theory_attempts')
    op.drop_index(op.f('ix_theory_attempts_id'), table_name='theory_attempts')
    op.drop_table('theory_attempts')
    op.drop_index(op.f('ix_theory_questions_topic'), table_name='theory_questions')
    op.drop_index(op.f('ix_theory_questions_id'), table_name='theory_questions')
    op.drop_table('theory_questions')
