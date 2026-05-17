"""
Sufficiency Checker — determines if retrieved documents have enough context.
Prevents the pipeline from generating answers based on insufficient evidence.
"""

import logging
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SUFFICIENCY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a legal research assistant evaluating whether retrieved document 
excerpts provide sufficient information to answer a user's question about a contract.

Evaluate: Do the retrieved passages contain the specific clause, term, or provision 
the user is asking about? Is there enough detail to give a substantive answer?"""),
    ("human", """USER QUESTION: {question}

RETRIEVED DOCUMENT EXCERPTS:
{context}

Evaluate if these excerpts are sufficient to answer the question.

Respond in valid JSON:
{{
  "sufficient": true,
  "confidence": 0.85,
  "reason": "Brief explanation",
  "missing_info": "What's missing if not sufficient (or null)"
}}"""),
])


@dataclass
class SufficiencyResult:
    sufficient: bool
    confidence: float
    reason: str
    missing_info: str | None


class SufficiencyChecker:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            max_retries=settings.nvidia_max_retries,
            timeout=settings.nvidia_timeout,
            temperature=0.0,
            max_tokens=256,
        )
        self.chain = SUFFICIENCY_PROMPT | self.llm | JsonOutputParser()

    async def check(self, docs: list[dict], question: str) -> SufficiencyResult:
        if not docs:
            return SufficiencyResult(sufficient=False, confidence=0.0, reason="No documents retrieved", missing_info="All relevant clauses")

        context = "\n\n---\n\n".join(d["text"][:500] for d in docs[:5])
        try:
            data = await self.chain.ainvoke({"question": question, "context": context})
            result = SufficiencyResult(
                sufficient=bool(data.get("sufficient", True)),
                confidence=float(data.get("confidence", 0.8)),
                reason=data.get("reason", ""),
                missing_info=data.get("missing_info"),
            )
        except Exception as e:
            logger.warning(f"Sufficiency check failed: {e} — defaulting to sufficient=True")
            result = SufficiencyResult(sufficient=True, confidence=0.5, reason="Check failed", missing_info=None)

        logger.info(f"[SufficiencyChecker] sufficient={result.sufficient}, confidence={result.confidence:.2f}")
        return result
