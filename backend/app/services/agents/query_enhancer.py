"""
Query Enhancer — HyDE-based query expansion for better retrieval.
Broadens or refines the query based on retrieval sufficiency feedback.
"""

import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.services.ingestion.embedder import embed_texts

logger = logging.getLogger(__name__)
settings = get_settings()


BROADEN_TEMPLATE = PromptTemplate.from_template(
    """The following search query did not find sufficient information in a legal document.
Rewrite it to be broader, using more general legal terminology and alternative phrasings.

Original Query: {query}

Write a broader version that might find relevant clauses. Output ONLY the new query."""
)

REFINE_TEMPLATE = PromptTemplate.from_template(
    """A legal analysis pipeline generated an answer but quality was insufficient.
Feedback: {feedback}

Original Query: {query}

Rewrite the query to address the feedback and find better supporting evidence.
Output ONLY the refined query."""
)


class QueryEnhancer:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.nvidia_model,
            openai_api_key=settings.nvidia_api_key,
            openai_api_base=settings.nvidia_base_url,
            temperature=0.2,
            max_tokens=256,
        )
        self.broaden_chain = BROADEN_TEMPLATE | self.llm | StrOutputParser()
        self.refine_chain = REFINE_TEMPLATE | self.llm | StrOutputParser()

    async def get_combined_query(self, standalone: str, hyde_doc: str) -> str:
        """Combine the standalone query with HyDE document for embedding."""
        # Weight: standalone query + HyDE doc gives richer retrieval signal
        return f"{standalone}\n\n{hyde_doc}"

    async def broaden(self, query: str) -> str:
        """Broaden query when insufficient docs are retrieved."""
        broadened = await self.broaden_chain.ainvoke({"query": query})
        logger.info(f"[QueryEnhancer] Broadened: '{broadened[:80]}...'")
        return broadened

    async def refine(self, query: str, feedback: str) -> str:
        """Refine query based on quality evaluator feedback."""
        refined = await self.refine_chain.ainvoke({"query": query, "feedback": feedback})
        logger.info(f"[QueryEnhancer] Refined: '{refined[:80]}...'")
        return refined
