"""
LangChain query rewriting pipeline.
Three-stage rewrite: Condense → Legal Expansion → HyDE
Uses conversation history from Neon DB for contextual follow-ups.
"""

import logging
from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RewrittenQuery:
    standalone_query: str      # Self-contained rewritten question
    expanded_query: str        # With legal synonyms for retrieval
    hyde_document: str         # Hypothetical ideal clause for HyDE


def _get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.nvidia_model,
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
        max_retries=settings.nvidia_max_retries,
            timeout=settings.nvidia_timeout,
            temperature=temperature,
        max_tokens=512,
    )


# ── Prompt Templates ──────────────────────────────────────────────────────

CONDENSE_TEMPLATE = PromptTemplate.from_template(
    """You are a legal assistant helping to clarify questions about contracts.

Given the conversation history below and a follow-up question, rewrite the 
follow-up question as a complete standalone question that captures all 
necessary context from the history.

Rules:
- If the question references "this clause", "it", "that section", "the above" → resolve what it refers to
- If it references a previously discussed risk or clause → include the clause name/type explicitly  
- If it is already standalone (no references to prior context) → return it unchanged
- Preserve legal specificity and terminology
- Output ONLY the rewritten question, nothing else

Conversation History:
{chat_history}

Follow-up Question: {question}

Standalone Question:"""
)

LEGAL_EXPANSION_TEMPLATE = PromptTemplate.from_template(
    """You are a legal search expert. Expand the following legal question with 
relevant synonyms and related legal terminology to improve document retrieval.

Original Question: {question}

Add synonyms and related terms for key legal concepts. Keep the question 
natural and under 3 sentences. Output ONLY the expanded question.

Expanded Question:"""
)

HYDE_TEMPLATE = PromptTemplate.from_template(
    """You are a legal expert. Write a hypothetical contract clause that would 
PERFECTLY answer the following question if it existed in a contract.

Question: {question}

Write a realistic, specific contract clause (2-4 sentences) as if it appeared 
in an actual legal document. Use formal legal language. Output ONLY the clause text.

Hypothetical Clause:"""
)


class QueryRewriter:
    """
    Three-stage LangChain query rewriting pipeline.
    
    Stage 1: Condense follow-up using conversation history (CONDENSE_TEMPLATE)
    Stage 2: Expand with legal synonyms (LEGAL_EXPANSION_TEMPLATE)
    Stage 3: Generate HyDE document (HYDE_TEMPLATE)
    """

    def __init__(self):
        self.llm = _get_llm(temperature=0.1)
        self.creative_llm = _get_llm(temperature=0.4)

        self.condense_chain = CONDENSE_TEMPLATE | self.llm | StrOutputParser()
        self.expand_chain = LEGAL_EXPANSION_TEMPLATE | self.llm | StrOutputParser()
        self.hyde_chain = HYDE_TEMPLATE | self.creative_llm | StrOutputParser()

    def _format_history(self, messages: list[BaseMessage]) -> str:
        """Format LangChain messages into a readable string for the prompt."""
        if not messages:
            return "No previous conversation."
        lines = []
        for msg in messages:
            role = "Human" if msg.type == "human" else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    async def rewrite(
        self,
        question: str,
        history: list[BaseMessage],
    ) -> RewrittenQuery:
        """
        Full three-stage rewrite pipeline.
        
        Args:
            question: Raw user question
            history: Recent conversation messages from Neon DB
        """
        # Stage 1: Condense with history context
        if history:
            chat_history_str = self._format_history(history)
            standalone = await self.condense_chain.ainvoke({
                "chat_history": chat_history_str,
                "question": question,
            })
            logger.info(f"[QueryRewriter] Condensed: '{standalone[:80]}...'")
        else:
            standalone = question
            logger.info("[QueryRewriter] No history — using original question")

        # Stage 2: Legal synonym expansion (for better retrieval)
        expanded = await self.expand_chain.ainvoke({"question": standalone})
        logger.info(f"[QueryRewriter] Expanded: '{expanded[:80]}...'")

        # Stage 3: HyDE — generate hypothetical ideal clause
        hyde_doc = await self.hyde_chain.ainvoke({"question": standalone})
        logger.info(f"[QueryRewriter] HyDE doc generated ({len(hyde_doc)} chars)")

        return RewrittenQuery(
            standalone_query=standalone,
            expanded_query=expanded,
            hyde_document=hyde_doc,
        )


# Module-level singleton
_rewriter: QueryRewriter | None = None


def get_rewriter() -> QueryRewriter:
    global _rewriter
    if _rewriter is None:
        _rewriter = QueryRewriter()
    return _rewriter
