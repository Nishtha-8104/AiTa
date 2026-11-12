"""llm_calls: provider and whose key answered

Revision ID: a7c1e2d3f4b5
Revises: f1a2b3c4d5e6
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7c1e2d3f4b5'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('llm_calls', sa.Column('provider', sa.String(length=30), nullable=False,
                                         server_default='nvidia'))
    op.add_column('llm_calls', sa.Column('key_source', sa.String(length=10), nullable=False,
                                         server_default='paet'))


def downgrade() -> None:
    op.drop_column('llm_calls', 'key_source')
    op.drop_column('llm_calls', 'provider')
