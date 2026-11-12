"""Chatbot threads and their messages; a message's tool calls and citations ride along as JSON.

Also the chunked open-licence programming books, embedded for the chatbot's search_books tool."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from app.core.database import Base

EMBED_DIM = 384


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    mode       = Column(String(10), nullable=False, default="pet", server_default="pet")
    title      = Column(String(120), nullable=True)
    summary    = Column(Text, nullable=True)
    # How many of the thread's oldest messages `summary` stands for.
    summary_upto = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_thread_created", "thread_id", "created_at"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    thread_id       = Column(Integer, ForeignKey("chat_threads.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    role            = Column(String(16), nullable=False)
    content         = Column(Text, nullable=False)
    tool_calls      = Column(JSON, nullable=True)
    citations       = Column(JSON, nullable=True)
    moderation_flag = Column(String(16), nullable=True)
    thumbs          = Column(String(4), nullable=True)
    model           = Column(String(120), nullable=True)
    tokens          = Column(Integer, nullable=True)
    latency_ms      = Column(Integer, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class EmbeddingVector(TypeDecorator):
    """pgvector on Postgres; JSON elsewhere so the sqlite test schema still builds."""

    impl = JSON
    cache_ok = True
    comparator_factory = Vector.comparator_factory

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(EMBED_DIM))
        return dialect.type_descriptor(JSON())


class BookChunk(Base):
    __tablename__ = "book_chunks"
    __table_args__ = (
        UniqueConstraint("source_id", "position", name="uq_book_chunks_source_position"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    source_id    = Column(String(64), nullable=False, index=True)
    source_title = Column(String(255), nullable=False)
    license      = Column(String(64), nullable=False)
    url          = Column(String(500), nullable=True)
    chapter      = Column(String(255), nullable=False, default="")
    section      = Column(String(255), nullable=False, default="")
    lang_tag     = Column(String(10), nullable=False, index=True)
    position     = Column(Integer, nullable=False)
    text         = Column(Text, nullable=False)
    tokens       = Column(Integer, nullable=False, default=0)
    embedding    = Column(EmbeddingVector(), nullable=True)
