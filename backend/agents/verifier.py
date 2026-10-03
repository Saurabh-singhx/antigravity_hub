import logging
import uuid
from typing import Any, Dict, List
import time

from agents.skills.answer_verifier import AnswerVerifierSkill
from models.qna import QnAItem, QnASource

logger = logging.getLogger("AntigravityHub.VerificationAgent")


class VerificationAgent:
    """
    Agent dedicated to verifying every question and answer candidate:
    ensures strict source-grounding, anti-hallucination compliance,
    accurate difficulty scoring, and slot alignment.
    """

    SLOT_NAMES = {1: "morning", 2: "afternoon", 3: "evening"}

    def __init__(self):
        self.verifier_skill = AnswerVerifierSkill()

    def verify_and_structure_candidates(
        self,
        candidates: List[Dict[str, Any]],
        slot_id: int,
        target_date: str,
        max_items: int = 5,
    ) -> List[QnAItem]:
        """
        Validates and transforms candidate dictionaries into production-grade QnAItem models.
        Rejects any items that fail anti-hallucination or source-grounding checks.
        """
        verified_items: List[QnAItem] = []

        for cand in candidates:
            # 1. Groundedness and source validation check
            is_valid, reason = self.verifier_skill.verify_groundedness(cand)
            if not is_valid:
                logger.warning(f"VerificationAgent rejected item '{cand.get('question', '')[:30]}...': {reason}")
                continue

            # 2. Assign difficulty
            difficulty = cand.get("difficulty") or self.verifier_skill.classify_difficulty(
                cand["question"], cand["answer"]
            )

            # 3. Create verified QnASource
            source = QnASource(
                source_type=cand.get("source_type", "github_repo"),
                source_name=cand["source_name"],
                source_url=cand["source_url"],
                source_quote=cand.get("source_quote"),
                stars=cand.get("stars"),
                reliability_score=cand.get("reliability_score", 1.0),
                verified=True,
            )

            # 4. Construct QnAItem
            item_id = f"qna_{slot_id}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
            qna_item = QnAItem(
                id=item_id,
                job_title=cand.get("job_title", "Full Stack Engineer"),
                company=cand.get("company"),
                slot_id=slot_id,
                slot_name=self.SLOT_NAMES.get(slot_id, "morning"),
                date=target_date,
                question=cand["question"],
                answer=cand["answer"],
                category=cand.get("category", "Fundamentals"),
                tech_stack=cand.get("tech_stack", ["General"]),
                source=source,
                difficulty=difficulty,
                is_mastered=False,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

            verified_items.append(qna_item)
            if len(verified_items) >= max_items:
                break

        logger.info(f"VerificationAgent approved {len(verified_items)} grounded questions for Slot {slot_id}.")
        return verified_items
