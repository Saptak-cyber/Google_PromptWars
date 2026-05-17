"""
Judge Agent — synthesizes prosecution and defense into a final verdict.
Impartial legal expert providing a risk score, verdict, and plain-English summary.
"""

import logging
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import get_settings
from app.services.agents.prosecutor_agent import ProsecutionResult
from app.services.agents.devils_advocate import AdvocateResult

logger = logging.getLogger(__name__)
settings = get_settings()

JUDGE_SYSTEM = """You are an impartial senior legal expert and arbitrator with deep expertise in 
consumer contract law, corporate law, and risk assessment.

You have heard arguments both FOR and AGAINST a contract clause.
Your role is to deliver a balanced, authoritative verdict that:
1. Acknowledges valid points from BOTH sides
2. Weighs net harm vs. net benefit to the user
3. Provides a clear actionable verdict
4. Gives practical negotiation suggestions when relevant
5. Explains everything in plain English a non-lawyer can understand

Verdicts:
- ACCEPT: Clause is reasonable, standard, low risk — user can safely agree
- NEGOTIATE: Clause has issues worth pushing back on — specific changes recommended  
- REJECT: Clause is seriously harmful, exploitative, or unacceptable — user should refuse or walk away"""

JUDGE_HUMAN = """USER'S QUESTION: {question}

PROSECUTION ARGUMENT (Consumer Rights Attorney):
Risk Level: {prosecution_risk_level}
{prosecution_argument}

Key Issues: {prosecution_issues}

DEFENSE ARGUMENT (Corporate Attorney):
Industry Standard: {defense_industry_standard}
{defense_argument}

User Benefits Claimed: {defense_benefits}

Now deliver your impartial verdict.

Respond in valid JSON with this exact structure:
{{
  "verdict": "ACCEPT|NEGOTIATE|REJECT",
  "risk_score": 7.5,
  "risk_label": "Critical|High|Medium|Low",
  "verdict_summary": "2-3 sentence balanced verdict summary",
  "plain_english": "Plain English explanation for a non-lawyer (1-2 paragraphs)",
  "prosecution_valid_points": ["valid point 1", "valid point 2"],
  "defense_valid_points": ["valid point 1", "valid point 2"],
  "negotiate_suggestions": ["Suggested change 1", "Suggested change 2"],
  "bottom_line": "One sentence: what should the user do?"
}}"""


@dataclass
class VerdictResult:
    verdict: str                          # ACCEPT | NEGOTIATE | REJECT
    risk_score: float                     # 0-10
    risk_label: str                       # Critical | High | Medium | Low
    verdict_summary: str
    plain_english: str
    prosecution_valid_points: list[str]
    defense_valid_points: list[str]
    negotiate_suggestions: list[str]
    bottom_line: str
    prosecution: ProsecutionResult = field(default=None)
    defense: AdvocateResult = field(default=None)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "risk_score": self.risk_score,
            "risk_label": self.risk_label,
            "verdict_summary": self.verdict_summary,
            "plain_english": self.plain_english,
            "prosecution_valid_points": self.prosecution_valid_points,
            "defense_valid_points": self.defense_valid_points,
            "negotiate_suggestions": self.negotiate_suggestions,
            "bottom_line": self.bottom_line,
            "prosecution": {
                "argument": self.prosecution.argument if self.prosecution else "",
                "risk_level": self.prosecution.risk_level if self.prosecution else "",
                "flagged_issues": self.prosecution.flagged_issues if self.prosecution else [],
                "consumer_impact": self.prosecution.consumer_impact if self.prosecution else "",
            } if self.prosecution else {},
            "defense": {
                "argument": self.defense.argument if self.defense else "",
                "justification": self.defense.justification if self.defense else "",
                "industry_standard": self.defense.industry_standard if self.defense else False,
                "user_benefits": self.defense.user_benefits if self.defense else [],
            } if self.defense else {},
        }


class JudgeAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            max_retries=settings.nvidia_max_retries,
            timeout=settings.nvidia_timeout,
            temperature=0.1,
            max_tokens=1200,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", JUDGE_SYSTEM),
            ("human", JUDGE_HUMAN),
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def synthesize(
        self,
        prosecution: ProsecutionResult,
        defense: AdvocateResult,
        question: str,
        stream_callback=None,
    ) -> VerdictResult:
        """Synthesize debate into final verdict, optionally streaming tokens."""
        inputs = {
            "question": question,
            "prosecution_risk_level": prosecution.risk_level,
            "prosecution_argument": prosecution.argument,
            "prosecution_issues": ", ".join(prosecution.flagged_issues),
            "defense_industry_standard": str(defense.industry_standard),
            "defense_argument": defense.argument,
            "defense_benefits": ", ".join(defense.user_benefits),
        }

        if stream_callback:
            streaming_llm = ChatOpenAI(
                model=settings.nvidia_model,
                api_key=settings.nvidia_api_key,
                base_url=settings.nvidia_base_url,
                max_retries=settings.nvidia_max_retries,
            timeout=settings.nvidia_timeout,
            temperature=0.1,
                max_tokens=1200,
                streaming=True,
            )
            streaming_chain = self.prompt | streaming_llm
            full_text = ""
            async for chunk in streaming_chain.astream(inputs):
                token = chunk.content
                if token:
                    full_text += token
                    await stream_callback("judge", token)

            import json, re
            json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
            data = json.loads(json_match.group()) if json_match else {}
        else:
            data = await self.chain.ainvoke(inputs)

        return VerdictResult(
            verdict=data.get("verdict", "NEGOTIATE"),
            risk_score=float(data.get("risk_score", 5.0)),
            risk_label=data.get("risk_label", "Medium"),
            verdict_summary=data.get("verdict_summary", ""),
            plain_english=data.get("plain_english", ""),
            prosecution_valid_points=data.get("prosecution_valid_points", []),
            defense_valid_points=data.get("defense_valid_points", []),
            negotiate_suggestions=data.get("negotiate_suggestions", []),
            bottom_line=data.get("bottom_line", ""),
            prosecution=prosecution,
            defense=defense,
        )
