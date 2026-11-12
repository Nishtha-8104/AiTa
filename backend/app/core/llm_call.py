"""One row per gateway call: who asked, which key and model answered, and how it ended."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id         = Column(Integer, primary_key=True, index=True)
    purpose    = Column(String(30), nullable=False, index=True)
    key_slot   = Column(Integer, nullable=True)
    model      = Column(String(120), nullable=False, default="")
    provider   = Column(String(30), nullable=False, default="nvidia", server_default="nvidia")
    key_source = Column(String(10), nullable=False, default="pet", server_default="pet")
    queued_ms  = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    tokens_in  = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    status     = Column(String(10), nullable=False)
    error      = Column(Text, nullable=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
