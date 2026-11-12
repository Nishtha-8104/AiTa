"""onboarding: learner preferences, onboarding records, diagnostic bank and responses

Revision ID: a1b2c3d4e5f6
Revises: f6a1b2c3d4e5
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f6a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'learner_preferences',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('program', sa.String(length=100), nullable=True),
        sa.Column('goal', sa.String(length=40), nullable=False),
        sa.Column('explanation_style', sa.String(length=20), nullable=False),
        sa.Column('example_order', sa.String(length=20), nullable=False),
        sa.Column('chat_language', sa.String(length=20), nullable=False),
        sa.Column('hours_per_week', sa.String(length=20), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    op.create_table(
        'diagnostic_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=80), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('topic', sa.String(length=40), nullable=False),
        sa.Column('tier', sa.Integer(), nullable=False),
        sa.Column('difficulty', sa.String(length=10), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('concept_key', sa.String(length=60), nullable=False),
        sa.Column('body', sa.JSON(), nullable=False),
        sa.Column('key', sa.JSON(), nullable=False),
        sa.Column('reviewed', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )
    op.create_index(op.f('ix_diagnostic_items_id'), 'diagnostic_items', ['id'])
    op.create_index('ix_diagnostic_items_lookup', 'diagnostic_items',
                    ['topic', 'kind', 'difficulty', 'language', 'reviewed'])

    op.create_table(
        'onboarding_records',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_step', sa.String(length=12), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('last_step_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('diagnostic_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_item_id', sa.Integer(), nullable=True),
        sa.Column('step_durations', sa.JSON(), nullable=True),
        sa.Column('self_rating', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=80), nullable=True),
        sa.Column('concept_level', sa.String(length=10), nullable=False),
        sa.Column('language_locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('seeds', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['current_item_id'], ['diagnostic_items.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    op.create_table(
        'diagnostic_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('phase', sa.String(length=12), nullable=False),
        sa.Column('answer', sa.JSON(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('graded_by', sa.String(length=10), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('reveal', sa.JSON(), nullable=True),
        sa.Column('ms_taken', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['diagnostic_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'item_id', name='uq_diagnostic_response_user_item'),
    )
    op.create_index(op.f('ix_diagnostic_responses_id'), 'diagnostic_responses', ['id'])
    op.create_index(op.f('ix_diagnostic_responses_user_id'), 'diagnostic_responses', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_diagnostic_responses_user_id'), table_name='diagnostic_responses')
    op.drop_index(op.f('ix_diagnostic_responses_id'), table_name='diagnostic_responses')
    op.drop_table('diagnostic_responses')
    op.drop_table('onboarding_records')
    op.drop_index('ix_diagnostic_items_lookup', table_name='diagnostic_items')
    op.drop_index(op.f('ix_diagnostic_items_id'), table_name='diagnostic_items')
    op.drop_table('diagnostic_items')
    op.drop_table('learner_preferences')
