"""
SQLAlchemy ORM models for LexGuard.
Tables: documents, conversations, messages
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.neon import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=True)
    chunk_count = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    conversations = relationship(
        "Conversation", back_populates="document", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    doc_id = Column(
        UUID(as_uuid=False),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    document = relationship("Document", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id = Column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(
        SAEnum(
            "user", "assistant", "prosecutor", "advocate", "judge",
            name="message_role_enum",
        ),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    # Stores structured data: risk_score, verdict, flagged_clauses, etc.
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
