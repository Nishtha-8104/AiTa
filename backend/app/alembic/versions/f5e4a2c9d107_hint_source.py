"""hint_events.source: practice ladder vs chat hints

Revision ID: f5e4a2c9d107
Revises: f2b1c4d6e803
Create Date: 2026-10-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f5e4a2c9d107'
down_revision: Union[str, Sequence[str], None] = 'f2b1c4d6e803'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hint_events', sa.Column(
        'source', sa.String(16), nullable=False, server_default='practice',
    ))


def downgrade() -> None:
    op.drop_column('hint_events', 'source')
