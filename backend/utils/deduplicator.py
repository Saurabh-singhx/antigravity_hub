"""
Deduplication Engine for Antigravity Hub Interview Q&A.

Multi-tiered duplicate and near-duplicate detection:
- Tier 1: Canonical Hash Matching (Exact & normalized token fingerprint, O(1))
- Tier 2: Fuzzy Token-Set & Token-Sort Ratio via RapidFuzz on Cleaned & Stemmed Tokens (85-100% syntactic similarity)
- Tier 3: Stop-word normalized token Jaccard & SequenceMatcher fallback
"""

import hashlib
import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger("AntigravityHub.Deduplicator")

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    logger.warning("rapidfuzz not installed, falling back to pure-Python fuzzy token matching.")


# Common question filler words, auxiliary verbs, generic prepositions, and discourse markers
QUESTION_STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "and", "or", "but", "nor", "so", "yet", "as", "if", "into", "through",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "should", "would", "may", "might", "must",
    "what", "how", "why", "when", "where", "which", "who", "whom",
    "explain", "describe", "compare", "contrast", "difference", "differences",
    "between", "versus", "vs", "work", "works", "working", "workings",
    "use", "used", "using", "overview", "mean", "means", "briefly", "detail", "details",
    "give", "example", "examples", "like", "such", "scenario", "star",
}


def clean_text(text: str) -> str:
    """Lowercases, strips punctuation, and collapses multiple whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def simple_stem(word: str) -> str:
    """Lightweight rule-based stemmer for common English grammatical suffixes."""
    w = word.lower()
    for suffix in ("ing", "tions", "tion", "ies", "es", "s", "ed"):
        if w.endswith(suffix) and len(w) > len(suffix) + 3:
            return w[:-len(suffix)]
    return w


def extract_canonical_tokens(text: str, stem: bool = False) -> List[str]:
    """Extracts sorted, unique significant tokens from question text."""
    cleaned = clean_text(text)
    words = cleaned.split()
    filtered = [w for w in words if w not in QUESTION_STOP_WORDS and len(w) > 1]
    if stem:
        filtered = [simple_stem(w) for w in filtered]
    return sorted(set(filtered))


def compute_canonical_hash(text: str) -> str:
    """
    Computes a deterministic SHA-256 hash of the canonicalized token set.
    Two questions with the exact same keywords (regardless of word order, filler words, or punctuation)
    will produce the exact same canonical hash.
    """
    tokens = extract_canonical_tokens(text, stem=True)
    fingerprint = " ".join(tokens)
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def compute_jaccard_similarity(tokens1: Set[str], tokens2: Set[str]) -> float:
    """Computes Jaccard index between two token sets."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union if union > 0 else 0.0


def compute_fuzzy_ratio(s1: str, s2: str) -> float:
    """
    Computes the maximum fuzzy similarity ratio (0.0 to 1.0)
    evaluating raw strings, canonical tokens, and stemmed tokens.
    """
    if not s1 or not s2:
        return 0.0

    c1 = clean_text(s1)
    c2 = clean_text(s2)

    if c1 == c2:
        return 1.0

    # Tokenized representations
    t1_tokens = extract_canonical_tokens(s1, stem=False)
    t2_tokens = extract_canonical_tokens(s2, stem=False)
    t1_str = " ".join(t1_tokens)
    t2_str = " ".join(t2_tokens)

    if t1_str and t1_str == t2_str:
        return 1.0

    # Stemmed representations
    stem1_tokens = extract_canonical_tokens(s1, stem=True)
    stem2_tokens = extract_canonical_tokens(s2, stem=True)
    stem1_str = " ".join(stem1_tokens)
    stem2_str = " ".join(stem2_tokens)

    if stem1_str and stem1_str == stem2_str:
        return 1.0

    if HAS_RAPIDFUZZ:
        scores = [
            fuzz.token_set_ratio(c1, c2) / 100.0,
            fuzz.token_sort_ratio(c1, c2) / 100.0,
            fuzz.token_set_ratio(t1_str, t2_str) / 100.0 if (t1_str and t2_str) else 0.0,
            fuzz.token_sort_ratio(t1_str, t2_str) / 100.0 if (t1_str and t2_str) else 0.0,
            fuzz.token_set_ratio(stem1_str, stem2_str) / 100.0 if (stem1_str and stem2_str) else 0.0,
            fuzz.token_sort_ratio(stem1_str, stem2_str) / 100.0 if (stem1_str and stem2_str) else 0.0,
        ]
        return max(scores)

    # Pure-Python fallback using Jaccard and SequenceMatcher
    import difflib
    set1 = set(t1_tokens)
    set2 = set(t2_tokens)
    stem_set1 = set(stem1_tokens)
    stem_set2 = set(stem2_tokens)

    jaccard1 = compute_jaccard_similarity(set1, set2)
    jaccard2 = compute_jaccard_similarity(stem_set1, stem_set2)
    seq_raw = difflib.SequenceMatcher(None, c1, c2).ratio()
    seq_token = difflib.SequenceMatcher(None, t1_str, t2_str).ratio() if (t1_str and t2_str) else 0.0

    return max(jaccard1, jaccard2, seq_raw, seq_token)


class DeduplicationEngine:
    """
    Production-grade deduplication engine for interview questions.
    Detects 85-100% duplicate and near-duplicate questions using:
    - Tier 1: Canonical Hash Lookup (Exact & reordered keyword match)
    - Tier 2: Fuzzy Token-Set & Token-Sort Ratio on normalized & stemmed representations
    - Tier 3: Substring containment and token Jaccard overlap
    """

    def __init__(self, similarity_threshold: float = 0.85):
        # 0.85 captures >= 85-100% semantic/token overlap reliably
        self.similarity_threshold = similarity_threshold

    def is_duplicate(
        self,
        candidate_question: str,
        existing_questions: Iterable[str],
        candidate_hash: Optional[str] = None,
        existing_hashes: Optional[Set[str]] = None,
    ) -> Tuple[bool, Optional[str], float, str]:
        """
        Evaluates whether candidate_question is identical or 85-100% similar
        to any question in existing_questions.

        Returns:
            (is_dup: bool, matched_question: Optional[str], score: float, reason: str)
        """
        if not candidate_question:
            return False, None, 0.0, "Empty question"

        cand_clean = clean_text(candidate_question)
        if not cand_clean:
            return False, None, 0.0, "Blank question after cleaning"

        cand_hash = candidate_hash or compute_canonical_hash(candidate_question)

        # Tier 1: Fast set lookup if hashes are provided
        if existing_hashes and cand_hash in existing_hashes:
            return True, None, 1.0, "Exact canonical token hash match (Tier 1)"

        cand_tokens = set(extract_canonical_tokens(candidate_question, stem=True))

        # Tier 2 & Tier 3: Check against existing question strings
        for past_q in existing_questions:
            if not past_q:
                continue

            past_clean = clean_text(past_q)
            if cand_clean == past_clean:
                return True, past_q, 1.0, "Identical normalized text match (100%)"

            past_hash = compute_canonical_hash(past_q)
            if cand_hash == past_hash:
                return True, past_q, 1.0, "Canonical keyword hash match (100% core topic)"

            # Fuzzy comparison across raw, canonical, and stemmed representations
            score = compute_fuzzy_ratio(candidate_question, past_q)
            if score >= self.similarity_threshold:
                pct = int(score * 100)
                return True, past_q, score, f"Fuzzy near-duplicate ({pct}% similarity >= {int(self.similarity_threshold * 100)}%)"

            # Check significant token Jaccard
            past_tokens = set(extract_canonical_tokens(past_q, stem=True))
            jaccard = compute_jaccard_similarity(cand_tokens, past_tokens)
            if jaccard >= 0.82:
                pct = int(jaccard * 100)
                return True, past_q, jaccard, f"High token overlap ({pct}% Jaccard similarity)"

        return False, None, 0.0, "Unique question"
