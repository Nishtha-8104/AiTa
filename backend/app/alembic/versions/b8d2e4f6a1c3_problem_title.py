"""problems.title

Revision ID: b8d2e4f6a1c3
Revises: a7c1e2d3f4b5
Create Date: 2026-11-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b8d2e4f6a1c3'
down_revision: Union[str, Sequence[str], None] = 'a7c1e2d3f4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('problems', sa.Column('title', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('problems', 'title')
