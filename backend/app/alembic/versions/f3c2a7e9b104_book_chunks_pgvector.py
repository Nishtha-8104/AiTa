"""book_chunks: pgvector extension, embedded book chunks, HNSW cosine index

Revision ID: f3c2a7e9b104
Revises: f4d3a6b8c215
Create Date: 2026-10-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = 'f3c2a7e9b104'
down_revision: Union[str, Sequence[str], None] = 'f4d3a6b8c215'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_context().dialect.name != 'postgresql':
        return
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table(
        'book_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('source_title', sa.String(length=255), nullable=False),
        sa.Column('license', sa.String(length=64), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('chapter', sa.String(length=255), nullable=False),
        sa.Column('section', sa.String(length=255), nullable=False),
        sa.Column('lang_tag', sa.String(length=10), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('tokens', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'position', name='uq_book_chunks_source_position'),
    )
    op.create_index(op.f('ix_book_chunks_id'), 'book_chunks', ['id'])
    op.create_index(op.f('ix_book_chunks_source_id'), 'book_chunks', ['source_id'])
    op.create_index(op.f('ix_book_chunks_lang_tag'), 'book_chunks', ['lang_tag'])
    op.create_index(
        'ix_book_chunks_embedding_hnsw', 'book_chunks', ['embedding'],
        postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    if op.get_context().dialect.name != 'postgresql':
        return
    op.drop_index('ix_book_chunks_embedding_hnsw', table_name='book_chunks')
    op.drop_index(op.f('ix_book_chunks_lang_tag'), table_name='book_chunks')
    op.drop_index(op.f('ix_book_chunks_source_id'), table_name='book_chunks')
    op.drop_index(op.f('ix_book_chunks_id'), table_name='book_chunks')
    op.drop_table('book_chunks')
