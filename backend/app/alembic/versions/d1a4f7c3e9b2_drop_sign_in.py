"""PET runs locally for one student: drop passwords and one-time codes

Revision ID: d1a4f7c3e9b2
Revises: c9e3f5a7b2d4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd1a4f7c3e9b2'
down_revision: Union[str, Sequence[str], None] = 'c9e3f5a7b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f('ix_otp_records_user_id'), table_name='otp_records')
    op.drop_index(op.f('ix_otp_records_id'), table_name='otp_records')
    op.drop_table('otp_records')
    with op.batch_alter_table('users') as batch:
        batch.drop_column('hashed_password')


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('hashed_password', sa.String(length=255), nullable=False,
                                   server_default=''))
    op.create_table(
        'otp_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('hashed_otp', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_otp_records_id'), 'otp_records', ['id'], unique=False)
    op.create_index(op.f('ix_otp_records_user_id'), 'otp_records', ['user_id'], unique=False)
