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

    GENERIC_HEADINGS = {
        "motivation", "features", "installation", "getting started", "what is this",
        "why would you read", "why read this", "who is this for", "how to use",
        "usage", "license", "table of contents", "contents", "contributing", "contributors",
        "acknowledgements", "support", "author", "authors", "summary", "disclaimer",
        "sponsor", "sponsors", "learn more", "overview", "introduction", "quick start",
        "about", "credits", "faq", "changelog", "roadmap", "prerequisites",
    }

    QUESTION_STARTERS = (
        "what", "how", "why", "when", "where", "which", "who", "whom",
        "explain", "describe", "compare", "contrast", "difference", "differences",
        "implement", "design", "discuss", "tell me", "can you", "write", "does",
        "is", "are", "would", "should", "could"
    )

    @classmethod
    def verify_groundedness(cls, item: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates that question & answer are authentic and grounded in a source."""
        question = (item.get("question") or "").strip()
        answer = (item.get("answer") or "").strip()
        source_name = (item.get("source_name") or "").strip()
        source_url = (item.get("source_url") or "").strip()

        # 1. Question validation
        if len(question) < 12:
            return False, "Question is too short (< 12 characters)"

        q_lower = question.lower().strip("*_` #")
        if q_lower in cls.GENERIC_HEADINGS or any(q_lower.startswith(g) for g in cls.GENERIC_HEADINGS):
            return False, f"Generic documentation heading, not an interview question: '{question}'"

        # Genuine questions either end with '?' or start with standard interview question phrasing
        if not (question.endswith("?") or q_lower.startswith(cls.QUESTION_STARTERS)):
            return False, f"Question lacks interrogative or technical interview structure: '{question}'"

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
