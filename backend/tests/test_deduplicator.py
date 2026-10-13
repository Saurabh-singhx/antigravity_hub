import unittest
from utils.deduplicator import (
    DeduplicationEngine,
    clean_text,
    compute_canonical_hash,
    compute_fuzzy_ratio,
    compute_jaccard_similarity,
    extract_canonical_tokens,
)


class TestDeduplicator(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(clean_text("  What is  the Virtual DOM???  "), "what is the virtual dom")
        self.assertEqual(clean_text("Node.js & Python!"), "node js python")
        self.assertEqual(clean_text(""), "")

    def test_extract_canonical_tokens(self):
        tokens = extract_canonical_tokens("How does Flutter's rendering pipeline work?")
        self.assertTrue("flutter" in tokens or "flutters" in tokens)
        self.assertTrue("rendering" in tokens)
        self.assertTrue("pipeline" in tokens)

    def test_canonical_hash_invariance(self):
        q1 = "What is the difference between B-Tree and Hash Index in PostgreSQL?"
        q2 = "In PostgreSQL, explain the difference between Hash Index and B-Tree?"
        h1 = compute_canonical_hash(q1)
        h2 = compute_canonical_hash(q2)
        self.assertEqual(h1, h2, f"Expected identical hash for reordered questions: {h1} vs {h2}")

    def test_deduplication_engine_exact_match(self):
        engine = DeduplicationEngine(similarity_threshold=0.85)
        existing = ["What is the Global Interpreter Lock (GIL) in CPython?"]
        is_dup, matched, score, reason = engine.is_duplicate(
            "What is the Global Interpreter Lock (GIL) in CPython?",
            existing,
        )
        self.assertTrue(is_dup)
        self.assertEqual(score, 1.0)

    def test_deduplication_engine_near_duplicate(self):
        engine = DeduplicationEngine(similarity_threshold=0.85)
        existing = ["How does React Reconciliation and the Virtual DOM Diffing algorithm work?"]
        variant = "How does React Reconciliation and Virtual DOM Diffing work?"
        is_dup, matched, score, reason = engine.is_duplicate(variant, existing)
        self.assertTrue(is_dup)
        self.assertGreaterEqual(score, 0.85)

    def test_deduplication_engine_distinct_questions(self):
        engine = DeduplicationEngine(similarity_threshold=0.85)
        existing = [
            "How does React Reconciliation and the Virtual DOM Diffing algorithm work?",
            "What is the Global Interpreter Lock (GIL) in CPython?",
        ]
        candidate = "How does database sharding compare with read replicas?"
        is_dup, matched, score, reason = engine.is_duplicate(candidate, existing)
        self.assertFalse(is_dup)
        self.assertLess(score, 0.60)
        self.assertEqual(reason, "Unique question")

    def test_deduplication_engine_hash_set_fast_path(self):
        engine = DeduplicationEngine(similarity_threshold=0.85)
        q = "What is Flutter Key architecture (ValueKey, ObjectKey, UniqueKey, and GlobalKey)?"
        q_hash = compute_canonical_hash(q)
        existing_hashes = {q_hash}
        is_dup, _, score, reason = engine.is_duplicate(
            candidate_question=q,
            existing_questions=[],
            candidate_hash=q_hash,
            existing_hashes=existing_hashes,
        )
        self.assertTrue(is_dup)
        self.assertEqual(score, 1.0)
        self.assertIn("Tier 1", reason)


if __name__ == "__main__":
    unittest.main()
