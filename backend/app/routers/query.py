"""
Query router — SSE streaming adversarial RAG pipeline endpoint.
Handles conversation management and streams debate + verdict to client.
"""

import asyncio
import json
import logging
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neon import get_db
from app.db.conversation_store import ConversationStore
from app.services.agents.rag_pipeline import RAGPipeline
from app.utils.streaming import sse_event, error_stream, done_stream

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level pipeline instance (agents are stateless, safe to share)
_pipeline = RAGPipeline()


class QueryRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ConversationCreate(BaseModel):
    doc_id: Optional[str] = None


@router.post("/conversations")
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation session."""
    store = ConversationStore(db)
    conv_id = await store.create_conversation(body.doc_id)
    return {"conversation_id": conv_id}


@router.post("/query")
async def query_document(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE streaming endpoint for the adversarial RAG pipeline.

    Streams events:
    - event: agent_status  → pipeline step progress
    - event: token         → streaming tokens from prosecutor/advocate/judge
    - event: verdict       → final structured verdict
    - event: error         → error info
    - event: done          → signals end of stream
    """
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    store = ConversationStore(db)

    # Get or create conversation
    conversation_id = await store.get_or_create(body.conversation_id, body.doc_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Token buffer for streaming
        token_queue: asyncio.Queue = asyncio.Queue()

        async def stream_callback(agent: str, token: str):
            """Called by agents to push tokens into the SSE stream."""
            if agent == "__status__":
                # Parse status JSON and emit as agent_status event
                try:
                    data = json.loads(token)
                    yield_str = sse_event("agent_status", data)
                except Exception:
                    yield_str = sse_event("agent_status", {"raw": token})
                await token_queue.put(yield_str)
            else:
                yield_str = sse_event("token", {"agent": agent, "token": token})
                await token_queue.put(yield_str)

        # Sentinel to signal pipeline completion
        DONE_SENTINEL = "__DONE__"
        verdict_holder = {}

        async def run_pipeline():
            try:
                verdict = await _pipeline.run(
                    question=body.question,
                    conversation_id=conversation_id,
                    doc_id=body.doc_id,
                    conversation_store=store,
                    stream_callback=stream_callback,
                )
                verdict_holder["result"] = verdict
            except Exception as e:
                logger.exception(f"Pipeline error: {e}")
                err_event = await error_stream(str(e))
                await token_queue.put(err_event)
            finally:
                await token_queue.put(DONE_SENTINEL)

        # Send conversation_id immediately so client can track it
        yield sse_event("conversation_id", {"conversation_id": conversation_id})

        # Start pipeline in background
        pipeline_task = asyncio.create_task(run_pipeline())

        # Stream tokens as they arrive
        while True:
            item = await token_queue.get()
            if item == DONE_SENTINEL:
                break
            yield item

        # Wait for pipeline to fully complete
        await pipeline_task

        # Emit final verdict event
        if "result" in verdict_holder:
            verdict = verdict_holder["result"]
            yield sse_event("verdict", verdict.to_dict())

        yield await done_stream()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch full conversation history."""
    store = ConversationStore(db)
    history = await store.get_full_history(conversation_id)
    return {"conversation_id": conversation_id, "messages": history}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    store = ConversationStore(db)
    await store.delete_conversation(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}
