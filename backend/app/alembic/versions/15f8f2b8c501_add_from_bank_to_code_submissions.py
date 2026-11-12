"""add from_bank to code_submissions

Revision ID: 15f8f2b8c501
Revises: c9349bc27f6d
Create Date: 2026-09-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15f8f2b8c501'
down_revision: Union[str, Sequence[str], None] = 'c9349bc27f6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('code_submissions', sa.Column(
        'from_bank', sa.Boolean(), nullable=False, server_default=sa.false(),
    ))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('code_submissions', 'from_bank')
