"""
Conversation history store using LangChain's PostgresChatMessageHistory.
Provides a clean interface to load/save conversation turns from Neon DB.
"""

import logging
import uuid
from typing import Optional

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_postgres import PostgresChatMessageHistory
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import get_settings
from app.db.models import Conversation, Message, Document

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversationStore:
    """
    Manages conversation lifecycle and wraps LangChain PostgresChatMessageHistory
    for use in the query rewriting pipeline.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Conversation CRUD ──────────────────────────────────────────────────

    async def create_conversation(self, doc_id: Optional[str] = None) -> str:
        """Create a new conversation and return its ID."""
        conv = Conversation(doc_id=doc_id)
        self.session.add(conv)
        await self.session.commit()
        await self.session.refresh(conv)
        logger.info(f"Created conversation {conv.id} for doc {doc_id}")
        return conv.id

    async def get_or_create(self, conversation_id: Optional[str], doc_id: Optional[str]) -> str:
        """Return existing conversation ID or create a new one."""
        if conversation_id:
            result = await self.session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conversation_id
        return await self.create_conversation(doc_id)

    async def save_turn(
        self,
        conversation_id: str,
        user_question: str,
        assistant_summary: str,
        metadata: Optional[dict] = None,
    ):
        """Persist a full user→assistant turn to Neon DB."""
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_question,
        )
        asst_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_summary,
            metadata_=metadata or {},
        )
        self.session.add_all([user_msg, asst_msg])
        await self.session.commit()

    async def save_agent_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ):
        """Save an individual agent message (prosecutor / advocate / judge)."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_=metadata or {},
        )
        self.session.add(msg)
        await self.session.commit()

    async def get_recent_history(self, conversation_id: str) -> list[BaseMessage]:
        """
        Fetch the last N turns as LangChain BaseMessage objects.
        Returns only user/assistant messages suitable for the query rewriter.
        """
        result = await self.session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(Message.created_at.desc())
            .limit(settings.max_history_messages)
        )
        rows = result.scalars().all()

        # Reverse to chronological order
        rows = list(reversed(rows))

        lc_messages: list[BaseMessage] = []
        for row in rows:
            if row.role == "user":
                lc_messages.append(HumanMessage(content=row.content))
            else:
                lc_messages.append(AIMessage(content=row.content))

        return lc_messages

    async def get_full_history(self, conversation_id: str) -> list[dict]:
        """Return full conversation history (all roles) as dicts for API response."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "role": row.role,
                "content": row.content,
                "metadata": row.metadata_,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def delete_conversation(self, conversation_id: str):
        await self.session.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        await self.session.commit()
