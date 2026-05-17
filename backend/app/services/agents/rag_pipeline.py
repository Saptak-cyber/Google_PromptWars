"""
Master RAG Orchestrator — the full agentic self-correcting loop.
Implements the 5-step pipeline from the architecture diagram with LangSmith tracing.
"""

import asyncio
import logging
from typing import Callable, Awaitable, Optional

from langsmith import traceable

from app.config import get_settings
from app.services.query.rewriter import QueryRewriter, get_rewriter
from app.services.agents.query_enhancer import QueryEnhancer
from app.services.agents.sufficiency_checker import SufficiencyChecker
from app.services.agents.prosecutor_agent import ProsecutorAgent
from app.services.agents.devils_advocate import DevilsAdvocateAgent
from app.services.agents.judge_agent import JudgeAgent, VerdictResult
from app.services.agents.quality_evaluator import QualityEvaluator
from app.services.retrieval import qdrant_store
from app.db.conversation_store import ConversationStore

logger = logging.getLogger(__name__)
settings = get_settings()

# Type alias for SSE streaming callback
StreamCallback = Callable[[str, str], Awaitable[None]]


class RAGPipeline:
    """
    LexGuard's adversarial self-correcting RAG pipeline.

    Flow:
    1. Contextual Query Rewriting (LangChain + Neon DB history)
    2. HyDE-enhanced retrieval from Qdrant
    3. Sufficiency check → broaden if needed
    4. Parallel Adversarial Debate (Prosecutor ↕ Devil's Advocate)
    5. Judge synthesis → Verdict
    6. Quality evaluation → Refine & retry if below threshold
    7. Persist to Neon DB conversation history
    """

    def __init__(self):
        self.rewriter = get_rewriter()
        self.enhancer = QueryEnhancer()
        self.sufficiency = SufficiencyChecker()
        self.prosecutor = ProsecutorAgent()
        self.advocate = DevilsAdvocateAgent()
        self.judge = JudgeAgent()
        self.quality = QualityEvaluator()

    @traceable(name="lexguard_rag_pipeline")
    async def run(
        self,
        question: str,
        conversation_id: str,
        doc_id: Optional[str],
        conversation_store: ConversationStore,
        stream_callback: Optional[StreamCallback] = None,
    ) -> VerdictResult:
        """
        Execute the full agentic RAG loop.

        Args:
            question: Raw user question
            conversation_id: Neon DB conversation ID
            doc_id: Optional filter to a specific indexed document
            conversation_store: DB session-bound store for history
            stream_callback: async fn(agent_name, token) for SSE streaming
        """

        async def emit_status(step: str, status: str, extra: dict = {}):
            """Emit pipeline step status event."""
            if stream_callback:
                await stream_callback("__status__", f'{{"step":"{step}","status":"{status}","extra":{extra}}}')

        # ── Step 1: Fetch history + Contextual Query Rewriting ──────────────
        await emit_status("query_rewrite", "active")
        history = await conversation_store.get_recent_history(conversation_id)
        rewritten = await self.rewriter.rewrite(question, history)
        logger.info(f"[Pipeline] Standalone query: {rewritten.standalone_query[:80]}")
        await emit_status("query_rewrite", "complete")

        # Build retrieval query (combined standalone + HyDE)
        retrieval_query = await self.enhancer.get_combined_query(
            rewritten.standalone_query, rewritten.hyde_document
        )

        best_verdict: Optional[VerdictResult] = None

        for attempt in range(settings.max_rag_retries):
            logger.info(f"[Pipeline] Attempt {attempt + 1}/{settings.max_rag_retries}")

            # ── Step 2: Retrieve from Qdrant ──────────────────────────────
            await emit_status("retrieval", "active", {"attempt": attempt + 1})
            docs = await qdrant_store.search(
                retrieval_query,
                doc_id_filter=doc_id,
            )
            await emit_status("retrieval", "complete", {"docs_found": len(docs)})

            # ── Step 3: Sufficiency Check ──────────────────────────────────
            await emit_status("sufficiency", "active")
            sufficiency = await self.sufficiency.check(docs, rewritten.standalone_query)
            await emit_status("sufficiency", "complete", {"sufficient": sufficiency.sufficient})

            if not sufficiency.sufficient and attempt < settings.max_rag_retries - 1:
                logger.info("[Pipeline] Insufficient docs — broadening query")
                retrieval_query = await self.enhancer.broaden(rewritten.standalone_query)
                continue

            # ── Step 4: Adversarial Debate (Parallel) ─────────────────────
            await emit_status("prosecutor", "active")
            await emit_status("advocate", "active")

            prosecution_task = self.prosecutor.argue(
                docs, rewritten.standalone_query, stream_callback
            )
            defense_task = self.advocate.argue(
                docs, rewritten.standalone_query, stream_callback
            )

            # Run both agents concurrently
            prosecution, defense = await asyncio.gather(prosecution_task, defense_task)

            await emit_status("prosecutor", "complete")
            await emit_status("advocate", "complete")

            # ── Step 5: Judge Synthesis ────────────────────────────────────
            await emit_status("judge", "active")
            verdict = await self.judge.synthesize(
                prosecution, defense, rewritten.standalone_query, stream_callback
            )
            await emit_status("judge", "complete")

            # Track best verdict seen so far
            if best_verdict is None or verdict.risk_score > 0:
                best_verdict = verdict

            # ── Step 6: Quality Evaluation ────────────────────────────────
            await emit_status("quality_check", "active")
            quality = await self.quality.evaluate(verdict.to_dict(), docs, rewritten.standalone_query)
            await emit_status("quality_check", "complete", {"score": quality.overall_score, "ok": quality.ok})

            if quality.ok or attempt == settings.max_rag_retries - 1:
                # ── Step 7: Persist to Neon DB ─────────────────────────────
                await conversation_store.save_turn(
                    conversation_id=conversation_id,
                    user_question=question,
                    assistant_summary=verdict.plain_english,
                    metadata=verdict.to_dict(),
                )
                await emit_status("done", "complete")
                return verdict

            # Quality insufficient — refine query and retry
            logger.info(f"[Pipeline] Quality below threshold ({quality.overall_score:.2f}) — refining query")
            retrieval_query = await self.enhancer.refine(
                rewritten.standalone_query, quality.feedback
            )

        # If all retries exhausted, return best verdict found
        if best_verdict:
            await conversation_store.save_turn(
                conversation_id=conversation_id,
                user_question=question,
                assistant_summary=best_verdict.plain_english,
                metadata=best_verdict.to_dict(),
            )
        await emit_status("done", "complete")
        return best_verdict
