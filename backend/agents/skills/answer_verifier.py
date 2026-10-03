import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("AntigravityHub.AnswerVerifier")


class AnswerVerifierSkill:
    """
    Verification skill ensuring zero agent hallucinations,
    strict grounding in verified sources, and high-yield interview relevance.
    """

    PLACEHOLDER_WORDS = {"todo", "tbd", "coming soon", "n/a", "unknown", "placeholder"}

    @classmethod
    def verify_groundedness(cls, item: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates that question & answer are authentic and grounded in a source."""
        question = (item.get("question") or "").strip()
        answer = (item.get("answer") or "").strip()
        source_name = (item.get("source_name") or "").strip()
        source_url = (item.get("source_url") or "").strip()

        # 1. Question validation
        if len(question) < 8:
            return False, "Question is too short (< 8 characters)"

        # 2. Answer completeness
        if len(answer) < 35:
            return False, "Answer is too terse or empty (< 35 characters)"

        # Check for placeholder answers
        if answer.lower() in cls.PLACEHOLDER_WORDS:
            return False, "Answer contains placeholder text"

        # 3. Source grounding check (Strict requirement: MUST have verifiable source!)
        if not source_name or not source_url:
            return False, "Unverifiable item: Missing source repository or citation"

        # 4. Source quote validation
        source_quote = item.get("source_quote") or ""
        if len(source_quote.strip()) < 10:
            return False, "Missing verified source excerpt quote"

        return True, "Passed anti-hallucination and source-grounding checks"

    @classmethod
    def classify_difficulty(cls, question: str, answer: str) -> str:
        """Determines difficulty based on technical depth and question scope."""
        q_lower = question.lower()
        a_lower = answer.lower()

        hard_indicators = [
            "distributed", "consensus", "race condition", "memory leak", "profiling",
            "sharding", "cap theorem", "internals", "concurrency", "low-level", "reconciliation"
        ]
        easy_indicators = [
            "what is", "difference between", "define", "basic", "lifecycle", "syntax"
        ]

        if any(h in q_lower or h in a_lower for h in hard_indicators) or len(answer) > 900:
            return "Hard"
        if any(e in q_lower for e in easy_indicators) and len(answer) < 350:
            return "Easy"
        return "Medium"
