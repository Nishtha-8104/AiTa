"""mcq_questions.verify_code: executable proof of the answer key

Revision ID: e5a2c9b3d418
Revises: d4e8a1c7f203
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5a2c9b3d418'
down_revision: Union[str, Sequence[str], None] = 'd4e8a1c7f203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mcq_questions', sa.Column(
        'verify_code', sa.Text(), nullable=False, server_default='',
    ))
    op.alter_column('mcq_questions', 'verify_code', server_default=None)


def downgrade() -> None:
    op.drop_column('mcq_questions', 'verify_code')
