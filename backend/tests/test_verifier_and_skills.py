import unittest
from agents.skills.answer_verifier import AnswerVerifierSkill
from agents.skills.qna_extractor import QnAExtractorSkill
from agents.verifier import VerificationAgent


class TestVerifierAndSkills(unittest.TestCase):
    def test_answer_verifier_valid_item(self):
        valid_cand = {
            "question": "What is the difference between B-Tree and Hash Index in PostgreSQL?",
            "answer": "B-Tree supports range queries in O(log n), whereas Hash Index provides O(1) equality lookups only.",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "B-Tree indexes support range queries while hash indexes provide O(1) equality.",
        }
        is_valid, reason = AnswerVerifierSkill.verify_groundedness(valid_cand)
        self.assertTrue(is_valid)

    def test_answer_verifier_rejects_generic_headings(self):
        for heading in ("Motivation", "Features", "Installation", "Why would you read this?", "Table of Contents"):
            cand = {
                "question": heading,
                "answer": "Some descriptive paragraph explaining the repository features in detail.",
                "source_name": "test_repo",
                "source_url": "https://github.com/test",
                "source_quote": "Some excerpt quote for verification testing.",
            }
            is_valid, reason = AnswerVerifierSkill.verify_groundedness(cand)
            self.assertFalse(is_valid, f"Heading '{heading}' should have been rejected! Reason: {reason}")

    def test_answer_verifier_rejects_terse_answers(self):
        cand = {
            "question": "What is the Event Loop in JavaScript?",
            "answer": "It loops events.",  # Too short (< 35 chars)
            "source_name": "test_repo",
            "source_url": "https://github.com/test",
            "source_quote": "The event loop has two queues.",
        }
        is_valid, reason = AnswerVerifierSkill.verify_groundedness(cand)
        self.assertFalse(is_valid)
        self.assertIn("too terse", reason)

    def test_qna_extractor_filters_markdown(self):
        content = """
# Getting Started
Here is how to install the package.

## Features
- Fast
- Easy

## What is the difference between Dart Isolates and OS Threads?
Dart Isolates have completely separate memory heaps and communicate via SendPort/ReceivePort message passing.

## Why would you read this?
Because it has questions.
"""
        extracted = QnAExtractorSkill.extract_pairs_from_markdown(
            content=content,
            source_name="test_repo",
            source_url="https://github.com/test/repo",
        )
        questions = [e["question"] for e in extracted]
        self.assertIn("What is the difference between Dart Isolates and OS Threads?", questions)
        self.assertNotIn("Features", questions)
        self.assertNotIn("Getting Started", questions)
        self.assertNotIn("Why would you read this?", questions)

    def test_verification_agent_deduplicates_intra_batch_and_prior(self):
        verifier = VerificationAgent(similarity_threshold=0.85)

        candidates = [
            {
                "question": "How does React Reconciliation and the Virtual DOM Diffing algorithm work?",
                "answer": "React uses heuristic O(n) diffing based on two assumptions to update the DOM efficiently.",
                "source_name": "Sudheerr/ReactJS-Interview-Questions",
                "source_url": "https://github.com/Sudheerr/ReactJS-Interview-Questions",
                "source_quote": "Reconciliation is the algorithm behind what is popularly understood as virtual DOM.",
                "slot_id": 1,
            },
            # Intra-batch near-duplicate of item 1:
            {
                "question": "How does React Reconciliation and Virtual DOM Diffing work?",
                "answer": "React uses heuristic diffing to update the real DOM efficiently across renders.",
                "source_name": "Sudheerr/ReactJS-Interview-Questions",
                "source_url": "https://github.com/Sudheerr/ReactJS-Interview-Questions",
                "source_quote": "Reconciliation algorithm compares virtual DOM trees in linear time.",
                "slot_id": 1,
            },
            # Unique item:
            {
                "question": "What is the difference between B-Tree and Hash Index in relational databases?",
                "answer": "B-Tree supports range queries and sorted scans, while Hash Index only supports O(1) equality.",
                "source_name": "donnemartin/system-design-primer",
                "source_url": "https://github.com/donnemartin/system-design-primer",
                "source_quote": "B-Tree indexes support range queries in O(log n) while hash indexes do not.",
                "slot_id": 1,
            },
        ]

        items = verifier.verify_and_structure_candidates(
            candidates=candidates,
            slot_id=1,
            target_date="2026-10-05",
            max_items=5,
        )
        self.assertEqual(len(items), 2)
        self.assertIsNotNone(items[0].canonical_hash)
        self.assertIsNotNone(items[1].canonical_hash)

        prior_q = ["What is the difference between B-Tree and Hash Index in relational databases?"]
        items2 = verifier.verify_and_structure_candidates(
            candidates=[candidates[2]],
            slot_id=1,
            target_date="2026-10-05",
            max_items=5,
            existing_questions=prior_q,
        )
        self.assertEqual(len(items2), 0, "Candidate identical to existing history question should be rejected!")


if __name__ == "__main__":
    unittest.main()
