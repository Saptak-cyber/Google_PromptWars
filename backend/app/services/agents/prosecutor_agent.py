"""
Prosecutor Agent — argues AGAINST contract clauses.
Consumer rights lawyer persona using NVIDIA NIM LLM.
"""

import logging
from dataclasses import dataclass
from typing import AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PROSECUTOR_SYSTEM = """You are an aggressive consumer rights attorney and contract law expert.
Your sole mission is to identify EVERY way a given contract clause could harm the user.

When analyzing a clause, you MUST consider:
1. Hidden costs, fees, or financial liabilities buried in the language
2. Rights the user is unknowingly waiving (right to sue, class action waiver, etc.)
3. Exploitative power asymmetries (unilateral modification rights, unlimited discretion)
4. Vague or ambiguous language that will always be interpreted against the user
5. Industry precedents where similar clauses were weaponized against consumers
6. Auto-renewal traps, termination penalties, or lock-in mechanisms
7. Data collection, sharing, or IP ownership clauses
8. Jurisdiction and governing law that disadvantages the user

Be thorough, adversarial, and specific. Cite the exact problematic language."""

PROSECUTOR_HUMAN = """CONTRACT CONTEXT (retrieved clauses):
{context}

USER'S QUESTION: {question}

Analyze the above contract clauses from the perspective of a consumer rights attorney.
Identify all potential harms, risks, and exploitative elements.

Respond in valid JSON with this exact structure:
{{
  "argument": "Your full prosecution argument (2-4 paragraphs)",
  "risk_level": "Critical|High|Medium|Low",
  "flagged_issues": ["issue 1", "issue 2", "issue 3"],
  "exact_problematic_phrases": ["phrase 1", "phrase 2"],
  "consumer_impact": "How this specifically impacts the average user"
}}"""


@dataclass
class ProsecutionResult:
    argument: str
    risk_level: str
    flagged_issues: list[str]
    exact_problematic_phrases: list[str]
    consumer_impact: str


class ProsecutorAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.nvidia_model,
            openai_api_key=settings.nvidia_api_key,
            openai_api_base=settings.nvidia_base_url,
            temperature=0.3,
            max_tokens=1024,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", PROSECUTOR_SYSTEM),
            ("human", PROSECUTOR_HUMAN),
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def argue(
        self,
        docs: list[dict],
        question: str,
        stream_callback=None,
    ) -> ProsecutionResult:
        """Run prosecution argument. Optionally streams tokens via callback."""
        context = "\n\n---\n\n".join(
            f"[Source: {d.get('source', 'Unknown')}, Page {d.get('page_number', '?')}]\n{d['text']}"
            for d in docs
        )

        if stream_callback:
            # Stream tokens as they arrive
            streaming_llm = ChatOpenAI(
                model=settings.nvidia_model,
                openai_api_key=settings.nvidia_api_key,
                openai_api_base=settings.nvidia_base_url,
                temperature=0.3,
                max_tokens=1024,
                streaming=True,
            )
            streaming_chain = self.prompt | streaming_llm
            full_text = ""
            async for chunk in streaming_chain.astream({"context": context, "question": question}):
                token = chunk.content
                if token:
                    full_text += token
                    await stream_callback("prosecutor", token)

            # Parse the JSON from the full streamed text
            import json, re
            json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"argument": full_text, "risk_level": "High", "flagged_issues": [], "exact_problematic_phrases": [], "consumer_impact": ""}
        else:
            data = await self.chain.ainvoke({"context": context, "question": question})

        return ProsecutionResult(
            argument=data.get("argument", ""),
            risk_level=data.get("risk_level", "Medium"),
            flagged_issues=data.get("flagged_issues", []),
            exact_problematic_phrases=data.get("exact_problematic_phrases", []),
            consumer_impact=data.get("consumer_impact", ""),
        )
