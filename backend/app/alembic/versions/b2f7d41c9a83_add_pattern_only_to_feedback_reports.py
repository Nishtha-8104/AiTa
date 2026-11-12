"""add pattern_only to feedback_reports

Revision ID: b2f7d41c9a83
Revises: 15f8f2b8c501
Create Date: 2026-09-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2f7d41c9a83'
down_revision: Union[str, Sequence[str], None] = '15f8f2b8c501'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('feedback_reports', sa.Column(
        'pattern_only', sa.Boolean(), nullable=False, server_default=sa.false(),
    ))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('feedback_reports', 'pattern_only')
