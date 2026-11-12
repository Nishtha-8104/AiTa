"""users.preferred_language: default editor/chat language

Revision ID: f2b1c4d6e803
Revises: f1a0b7c3d921
Create Date: 2026-10-11 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f2b1c4d6e803'
down_revision: Union[str, Sequence[str], None] = 'f1a0b7c3d921'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column(
        'preferred_language', sa.String(10), nullable=False, server_default='c',
    ))


def downgrade() -> None:
    op.drop_column('users', 'preferred_language')
