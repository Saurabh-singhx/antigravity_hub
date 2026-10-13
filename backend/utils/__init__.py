from .deduplicator import (
    DeduplicationEngine,
    clean_text,
    compute_canonical_hash,
    compute_fuzzy_ratio,
    compute_jaccard_similarity,
    extract_canonical_tokens,
)

__all__ = [
    "DeduplicationEngine",
    "clean_text",
    "compute_canonical_hash",
    "compute_fuzzy_ratio",
    "compute_jaccard_similarity",
    "extract_canonical_tokens",
]
