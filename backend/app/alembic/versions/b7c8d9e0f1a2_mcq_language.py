"""mcq_questions.language: c, cpp, python, or any for concept questions

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-10-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mcq_questions', sa.Column(
        'language', sa.String(10), nullable=False, server_default='python',
    ))
    op.create_index('ix_mcq_questions_topic_language', 'mcq_questions', ['topic', 'language'])


def downgrade() -> None:
    op.drop_index('ix_mcq_questions_topic_language', table_name='mcq_questions')
    op.drop_column('mcq_questions', 'language')
