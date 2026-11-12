"""drop the recommendations and Content Player tables, and feedback_reports.cp_session_id

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-10-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e0f1a2b3c4d5'
down_revision: Union[str, Sequence[str], None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Children before parents, so no foreign key is left pointing at a dropped table.
_TABLES = ('content_player_messages', 'code_snapshots', 'content_player_sessions',
           'recommendations', 'user_content_interactions', 'agent_run_logs', 'contents')
_ENUMS = ('contenttype', 'difficultylevel', 'interactiontype')


def upgrade() -> None:
    op.drop_column('feedback_reports', 'cp_session_id')
    for table in _TABLES:
        op.drop_table(table)
    if op.get_bind().dialect.name == 'postgresql':
        for name in _ENUMS:
            op.execute(f'DROP TYPE IF EXISTS {name}')


def _created_at():
    return sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                     nullable=True)


def _user_fk():
    return sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')


def downgrade() -> None:
    op.create_table(
        'contents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content_type', sa.Enum('VIDEO', 'ARTICLE', 'EXERCISE', 'QUIZ', 'PROJECT',
                                          'TUTORIAL', name='contenttype'), nullable=False),
        sa.Column('difficulty', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED',
                                        name='difficultylevel'), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=1000), nullable=True),
        sa.Column('duration_mins', sa.Float(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('topics', sa.JSON(), nullable=True),
        sa.Column('skills_gained', sa.JSON(), nullable=True),
        sa.Column('prerequisites', sa.JSON(), nullable=True),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('avg_rating', sa.Float(), nullable=True),
        sa.Column('total_ratings', sa.Integer(), nullable=True),
        sa.Column('completion_rate', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        _created_at(),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_contents_id'), 'contents', ['id'], unique=False)
    op.create_table(
        'agent_run_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('step_log', sa.JSON(), nullable=True),
        sa.Column('cf_candidates', sa.Integer(), nullable=True),
        sa.Column('cbf_candidates', sa.Integer(), nullable=True),
        sa.Column('final_count', sa.Integer(), nullable=True),
        sa.Column('llm_tokens_used', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        _created_at(),
        _user_fk(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id'),
    )
    op.create_index(op.f('ix_agent_run_logs_id'), 'agent_run_logs', ['id'], unique=False)
    op.create_table(
        'user_content_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('interaction', sa.Enum('VIEW', 'COMPLETE', 'LIKE', 'DISLIKE', 'SKIP', 'BOOKMARK',
                                         name='interactiontype'), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('implicit_score', sa.Float(), nullable=True),
        sa.Column('time_spent_mins', sa.Float(), nullable=True),
        sa.Column('completion_pct', sa.Float(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('is_bookmarked', sa.Boolean(), nullable=True),
        sa.Column('interacted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        _user_fk(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'content_id', name='uq_user_content'),
    )
    op.create_index(op.f('ix_user_content_interactions_id'), 'user_content_interactions', ['id'],
                    unique=False)
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('cf_score', sa.Float(), nullable=True),
        sa.Column('cbf_score', sa.Float(), nullable=True),
        sa.Column('rl_bonus', sa.Float(), nullable=True),
        sa.Column('agent_reasoning', sa.Text(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('batch_id', sa.String(length=64), nullable=True),
        sa.Column('is_dismissed', sa.Boolean(), nullable=True),
        sa.Column('is_clicked', sa.Boolean(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        _user_fk(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recommendations_id'), 'recommendations', ['id'], unique=False)
    op.create_table(
        'content_player_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('mode', sa.String(length=30), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('topic', sa.String(length=255), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('total_messages', sa.Integer(), nullable=True),
        sa.Column('total_tokens_used', sa.Integer(), nullable=True),
        sa.Column('concepts_covered', sa.JSON(), nullable=True),
        sa.Column('agent_model', sa.String(length=100), nullable=True),
        sa.Column('confusion_detected', sa.Boolean(), nullable=True),
        sa.Column('mastery_signals', sa.JSON(), nullable=True),
        sa.Column('weak_signals', sa.JSON(), nullable=True),
        sa.Column('solved_questions', sa.JSON(), nullable=True),
        sa.Column('consecutive_easy_solves', sa.Integer(), nullable=True),
        _created_at(),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        _user_fk(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_content_player_sessions_id'), 'content_player_sessions', ['id'],
                    unique=False)
    op.create_table(
        'code_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('agent_feedback', sa.Text(), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['session_id'], ['content_player_sessions.id'], ondelete='CASCADE'),
        _user_fk(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_code_snapshots_id'), 'code_snapshots', ['id'], unique=False)
    op.create_table(
        'content_player_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('has_code', sa.Boolean(), nullable=True),
        sa.Column('code_snippet', sa.Text(), nullable=True),
        sa.Column('code_language', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('was_helpful', sa.Boolean(), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['session_id'], ['content_player_sessions.id'], ondelete='CASCADE'),
        _user_fk(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_content_player_messages_id'), 'content_player_messages', ['id'],
                    unique=False)
    op.add_column('feedback_reports', sa.Column('cp_session_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'feedback_reports', 'content_player_sessions',
                          ['cp_session_id'], ['id'], ondelete='SET NULL')
