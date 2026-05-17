"""
Devil's Advocate Agent — argues FOR contract clauses.
Corporate contract lawyer persona using NVIDIA NIM LLM.
"""

import logging
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ADVOCATE_SYSTEM = """You are a seasoned corporate contract attorney with 20 years of experience
drafting and defending commercial agreements.

Your role is to present the strongest possible case FOR why a given contract clause is:
- Standard, industry-accepted practice (used by virtually all companies in this sector)
- Necessary for legitimate business operations, risk management, or legal compliance
- Protective of BOTH parties' interests, not just the company
- Less harmful or alarming than it appears on first reading
- Legally required or driven by regulatory compliance
- A reasonable exchange for the value/service the user receives

Be specific, cite industry norms, and explain the business rationale. 
Do not be dismissive — acknowledge concerns while reframing them."""

ADVOCATE_HUMAN = """CONTRACT CONTEXT (retrieved clauses):
{context}

USER'S QUESTION: {question}

As a corporate contract attorney, present the strongest defense of these clauses.
Explain why they are reasonable, standard, or necessary.

Respond in valid JSON with this exact structure:
{{
  "argument": "Your full defense argument (2-4 paragraphs)",
  "justification": "Core business/legal reason this clause exists",
  "industry_standard": true,
  "comparable_companies": ["Company A", "Company B"],
  "user_benefits": ["benefit 1", "benefit 2"],
  "regulatory_basis": "Any legal/regulatory requirement driving this clause (or null)"
}}"""


@dataclass
class AdvocateResult:
    argument: str
    justification: str
    industry_standard: bool
    comparable_companies: list[str]
    user_benefits: list[str]
    regulatory_basis: str | None


class DevilsAdvocateAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            max_retries=settings.nvidia_max_retries,
            timeout=settings.nvidia_timeout,
            temperature=0.3,
            max_tokens=1024,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", ADVOCATE_SYSTEM),
            ("human", ADVOCATE_HUMAN),
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def argue(
        self,
        docs: list[dict],
        question: str,
        stream_callback=None,
    ) -> AdvocateResult:
        """Run defense argument. Optionally streams tokens via callback."""
        context = "\n\n---\n\n".join(
            f"[Source: {d.get('source', 'Unknown')}, Page {d.get('page_number', '?')}]\n{d['text']}"
            for d in docs
        )

        if stream_callback:
            streaming_llm = ChatOpenAI(
                model=settings.nvidia_model,
                api_key=settings.nvidia_api_key,
                base_url=settings.nvidia_base_url,
                max_retries=settings.nvidia_max_retries,
            timeout=settings.nvidia_timeout,
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
                    await stream_callback("advocate", token)

            import json, re
            json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"argument": full_text, "justification": "", "industry_standard": True, "comparable_companies": [], "user_benefits": [], "regulatory_basis": None}
        else:
            data = await self.chain.ainvoke({"context": context, "question": question})

        return AdvocateResult(
            argument=data.get("argument", ""),
            justification=data.get("justification", ""),
            industry_standard=data.get("industry_standard", True),
            comparable_companies=data.get("comparable_companies", []),
            user_benefits=data.get("user_benefits", []),
            regulatory_basis=data.get("regulatory_basis"),
        )
