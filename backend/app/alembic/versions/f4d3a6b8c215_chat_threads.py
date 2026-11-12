"""chat_threads + chat_messages: chatbot persistence

Revision ID: f4d3a6b8c215
Revises: f5e4a2c9d107
Create Date: 2026-10-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f4d3a6b8c215'
down_revision: Union[str, Sequence[str], None] = 'f5e4a2c9d107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=10), nullable=False, server_default='aita'),
        sa.Column('title', sa.String(length=120), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_upto', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_threads_id'), 'chat_threads', ['id'])
    op.create_index(op.f('ix_chat_threads_user_id'), 'chat_threads', ['user_id'])

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', sa.JSON(), nullable=True),
        sa.Column('citations', sa.JSON(), nullable=True),
        sa.Column('moderation_flag', sa.String(length=16), nullable=True),
        sa.Column('thumbs', sa.String(length=4), nullable=True),
        sa.Column('model', sa.String(length=120), nullable=True),
        sa.Column('tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'])
    op.create_index(op.f('ix_chat_messages_thread_id'), 'chat_messages', ['thread_id'])
    op.create_index(op.f('ix_chat_messages_user_id'), 'chat_messages', ['user_id'])
    op.create_index('ix_chat_messages_thread_created', 'chat_messages',
                    ['thread_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_chat_messages_thread_created', table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_user_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_thread_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_chat_threads_user_id'), table_name='chat_threads')
    op.drop_index(op.f('ix_chat_threads_id'), table_name='chat_threads')
    op.drop_table('chat_threads')
