import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AntigravityHub.QnAExtractor")


class QnAExtractorSkill:
    """Skill for high-precision extraction and structuring of Q&A pairs from source markdown."""

    QUESTION_HEADER_PATTERNS = [
        re.compile(r"^#{1,4}\s*(?:Q(?:\d+)?:|\d+[\.\)]\s*)?(.+\?.*)$", re.MULTILINE),
        re.compile(r"^#{1,4}\s*(?:What|How|Why|When|Explain|Describe|Compare|Difference between)\s+(.+)$", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^\*\*(?:Q(?:\d+)?:|\d+[\.\)]\s*)?(.+\?.*)\*\*$", re.MULTILINE),
    ]

    @classmethod
    def extract_pairs_from_markdown(
        cls,
        content: str,
        source_name: str,
        source_url: str,
        default_category: str = "Fundamentals",
        tech_tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Parses raw markdown text and extracts verified question-answer blocks."""
        pairs = []
        if not content or len(content.strip()) < 50:
            return pairs

        # Split content into sections by headers
        sections = re.split(r"\n(?=#{2,4}\s+)", content)
        for section in sections:
            section_clean = section.strip()
            if not section_clean:
                continue

            lines = section_clean.split("\n")
            header_line = lines[0].strip()

            # Clean header to get question
            clean_question = re.sub(r"^#{1,4}\s*", "", header_line).strip()
            clean_question = re.sub(r"^(?:Q(?:\d+)?:|\d+[\.\)]\s*)", "", clean_question).strip()
            clean_question = clean_question.strip("*_` ")

            # Skip if header is generic title or navigation
            if len(clean_question) < 10 or clean_question.lower() in (
                "table of contents", "contents", "license", "contributing", "overview", "introduction"
            ):
                continue

            answer_body = "\n".join(lines[1:]).strip()
            # Must have substantial answer (at least 40 chars)
            if len(answer_body) < 40:
                continue

            # Generate authentic source quote (first 150 chars of answer)
            quote = answer_body[:160].replace("\n", " ").strip() + "..."

            pairs.append({
                "question": clean_question,
                "answer": answer_body,
                "category": default_category,
                "tech_stack": tech_tags or ["Full Stack"],
                "source_name": source_name,
                "source_url": source_url,
                "source_quote": quote,
            })

        return pairs
