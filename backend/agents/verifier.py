import logging
import time
from typing import Any, Dict, List, Optional, Set
import uuid

from agents.skills.answer_verifier import AnswerVerifierSkill
from models.qna import QnAItem, QnASource
from utils.deduplicator import DeduplicationEngine, compute_canonical_hash

logger = logging.getLogger("AntigravityHub.VerificationAgent")


class VerificationAgent:
    """
    Agent dedicated to verifying every question and answer candidate:
    - Ensures strict source-grounding and anti-hallucination compliance
    - Enforces multi-tier deduplication (prevents 85-100% duplicate questions)
    - Prevents intra-batch duplicates and repeats from historical question store
    - Validates accurate difficulty scoring and slot alignment
    """

    SLOT_NAMES = {1: "morning", 2: "afternoon", 3: "evening"}

    def __init__(self, similarity_threshold: float = 0.85):
        self.verifier_skill = AnswerVerifierSkill()
        self.dedup_engine = DeduplicationEngine(similarity_threshold=similarity_threshold)

    def verify_and_structure_candidates(
        self,
        candidates: List[Dict[str, Any]],
        slot_id: int,
        target_date: str,
        max_items: int = 5,
        existing_questions: Optional[List[str]] = None,
        existing_hashes: Optional[Set[str]] = None,
    ) -> List[QnAItem]:
        """
        Validates, deduplicates, and transforms candidate dictionaries into production-grade QnAItem models.
        Rejects any items that fail anti-hallucination, source-grounding, or deduplication checks.
        """
        verified_items: List[QnAItem] = []
        prior_questions = list(existing_questions or [])
        prior_hashes = set(existing_hashes or set())

        for cand in candidates:
            cand_q = (cand.get("question") or "").strip()
            cand_a = (cand.get("answer") or "").strip()

            # 1. Groundedness and source validation check
            is_valid, reason = self.verifier_skill.verify_groundedness(cand)
            if not is_valid:
                logger.warning(f"VerificationAgent rejected item '{cand_q[:35]}...': {reason}")
                continue

            # 2. Multi-tier Deduplication & Near-duplicate rejection (85-100% similarity)
            cand_hash = compute_canonical_hash(cand_q)
            current_batch_questions = [item.question for item in verified_items]
            current_batch_hashes = {item.canonical_hash for item in verified_items if item.canonical_hash}

            combined_questions = prior_questions + current_batch_questions
            combined_hashes = prior_hashes | current_batch_hashes

            is_dup, matched_q, score, dup_reason = self.dedup_engine.is_duplicate(
                candidate_question=cand_q,
                existing_questions=combined_questions,
                candidate_hash=cand_hash,
                existing_hashes=combined_hashes,
            )

            if is_dup:
                matched_snippet = f" (matched: '{matched_q[:40]}...')" if matched_q else ""
                logger.info(
                    f"VerificationAgent rejected duplicate question '{cand_q[:45]}...': {dup_reason}{matched_snippet}"
                )
                continue

            # 3. Assign difficulty
            difficulty = cand.get("difficulty") or self.verifier_skill.classify_difficulty(
                cand_q, cand_a
            )

            # 4. Create verified QnASource
            source = QnASource(
                source_type=cand.get("source_type", "github_repo"),
                source_name=cand["source_name"],
                source_url=cand["source_url"],
                source_quote=cand.get("source_quote"),
                stars=cand.get("stars"),
                reliability_score=cand.get("reliability_score", 1.0),
                verified=True,
            )

            # 5. Construct QnAItem with canonical hash
            item_id = f"qna_{slot_id}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
            qna_item = QnAItem(
                id=item_id,
                job_title=cand.get("job_title", "Full Stack Engineer"),
                company=cand.get("company"),
                slot_id=slot_id,
                slot_name=self.SLOT_NAMES.get(slot_id, "morning"),
                date=target_date,
                question=cand_q,
                answer=cand_a,
                category=cand.get("category", "Fundamentals"),
                tech_stack=cand.get("tech_stack", ["General"]),
                source=source,
                difficulty=difficulty,
                is_mastered=False,
                canonical_hash=cand_hash,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

            verified_items.append(qna_item)
            if len(verified_items) >= max_items:
                break

        logger.info(
            f"VerificationAgent approved {len(verified_items)} grounded, unique questions for Slot {slot_id} (limit={max_items})."
        )
        return verified_items
