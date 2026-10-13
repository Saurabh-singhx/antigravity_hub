import os
import tempfile
import unittest
from database.manager import DatabaseManager
from models.qna import QnAItem, QnASource


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_hub.db")
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_save_and_retrieve_qna_with_canonical_hash(self):
        source = QnASource(
            source_type="github_repo",
            source_name="donnemartin/system-design-primer",
            source_url="https://github.com/donnemartin/system-design-primer",
            source_quote="B-Tree indexes support range queries in O(log n).",
        )
        item = QnAItem(
            id="qna_test_1",
            job_title="Backend Engineer",
            slot_id=1,
            slot_name="morning",
            date="2026-10-05",
            question="What is the difference between B-Tree and Hash Index in PostgreSQL?",
            answer="B-Tree supports range queries in O(log n), whereas Hash Index provides O(1) equality.",
            category="Fundamentals",
            tech_stack=["SQL", "Databases"],
            source=source,
            difficulty="Medium",
            canonical_hash="testhash123456789",
        )
        saved = self.db.save_qna_items([item])
        self.assertEqual(saved, 1)

        daily = self.db.get_daily_qna("2026-10-05")
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0].canonical_hash, "testhash123456789")

        recents = self.db.get_recent_question_texts()
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["canonical_hash"], "testhash123456789")

    def test_clean_duplicate_questions(self):
        source = QnASource(
            source_type="github_repo",
            source_name="donnemartin/system-design-primer",
            source_url="https://github.com/donnemartin/system-design-primer",
            source_quote="B-Tree indexes support range queries in O(log n).",
        )
        # Insert duplicate questions with different IDs and same canonical hash
        item1 = QnAItem(
            id="qna_test_1",
            job_title="Backend Engineer",
            slot_id=1,
            slot_name="morning",
            date="2026-10-05",
            question="What is the difference between B-Tree and Hash Index in PostgreSQL?",
            answer="B-Tree supports range queries in O(log n).",
            category="Fundamentals",
            tech_stack=["SQL"],
            source=source,
            canonical_hash="same_hash_123",
        )
        item2 = QnAItem(
            id="qna_test_2",
            job_title="Backend Engineer",
            slot_id=1,
            slot_name="morning",
            date="2026-10-05",
            question="What is the difference between B-Tree and Hash Index in PostgreSQL?",
            answer="B-Tree supports range queries in O(log n).",
            category="Fundamentals",
            tech_stack=["SQL"],
            source=source,
            canonical_hash="same_hash_123",
        )
        self.db.save_qna_items([item1, item2])
        self.assertEqual(len(self.db.get_daily_qna("2026-10-05")), 2)

        deleted = self.db.clean_duplicate_questions()
        self.assertEqual(deleted, 1)
        remaining = self.db.get_daily_qna("2026-10-05")
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, "qna_test_1")


if __name__ == "__main__":
    unittest.main()
