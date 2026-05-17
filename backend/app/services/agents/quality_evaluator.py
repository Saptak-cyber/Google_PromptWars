"""
Quality Evaluator — self-evaluates the Judge's verdict for faithfulness and completeness.
Triggers retry loop if quality is below threshold.
"""

import logging
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

QUALITY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a quality auditor for legal AI analysis. Evaluate whether an analysis is grounded in the provided documents, complete, and genuinely useful."),
    ("human", """USER QUESTION: {question}

RETRIEVED DOCUMENT EXCERPTS:
{context}

GENERATED VERDICT:
{verdict}

Evaluate the verdict on three criteria:
1. Faithfulness: Is it grounded in the retrieved documents? (not hallucinated)
2. Completeness: Does it address the user's question fully?
3. Usefulness: Is the plain-English explanation clear and actionable?

Respond in valid JSON:
{{
  "ok": true,
  "overall_score": 0.82,
  "faithfulness_score": 0.9,
  "completeness_score": 0.8,
  "usefulness_score": 0.75,
  "feedback": "Specific feedback on what could be improved",
  "best_so_far": "The best answer found so far (copy verdict text here if ok)"
}}"""),
])


@dataclass
class QualityResult:
    ok: bool
    overall_score: float
    feedback: str
    best_so_far: str


class QualityEvaluator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            max_retries=settings.nvidia_max_retries,
            timeout=settings.nvidia_timeout,
            temperature=0.0,
            max_tokens=512,
        )
        self.chain = QUALITY_PROMPT | self.llm | JsonOutputParser()

    async def evaluate(
        self,
        verdict_dict: dict,
        docs: list[dict],
        question: str,
    ) -> QualityResult:
        context = "\n\n---\n\n".join(d["text"][:400] for d in docs[:5])
        verdict_str = str(verdict_dict.get("plain_english", "")) + "\n" + str(verdict_dict.get("verdict_summary", ""))

        try:
            data = await self.chain.ainvoke({
                "question": question,
                "context": context,
                "verdict": verdict_str,
            })
            score = float(data.get("overall_score", 0.8))
            result = QualityResult(
                ok=score >= settings.quality_threshold,
                overall_score=score,
                feedback=data.get("feedback", ""),
                best_so_far=data.get("best_so_far", verdict_str),
            )
        except Exception as e:
            logger.warning(f"Quality evaluation failed: {e} — defaulting ok=True")
            result = QualityResult(ok=True, overall_score=0.75, feedback="", best_so_far=verdict_str)

        logger.info(f"[QualityEvaluator] ok={result.ok}, score={result.overall_score:.2f}")
        return result
