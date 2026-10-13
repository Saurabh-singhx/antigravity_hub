"""Re-export deduplication engine from utils.deduplicator."""

from utils.deduplicator import (
    DeduplicationEngine,
    clean_text,
    compute_canonical_hash,
    compute_fuzzy_ratio,
    compute_jaccard_similarity,
    extract_canonical_tokens,
    simple_stem,
)

__all__ = [
    "DeduplicationEngine",
    "clean_text",
    "compute_canonical_hash",
    "compute_fuzzy_ratio",
    "compute_jaccard_similarity",
    "extract_canonical_tokens",
    "simple_stem",
]
