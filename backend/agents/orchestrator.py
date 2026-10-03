import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from agents.curator_dispatch import CuratorDispatchAgent
from agents.job_collector import JobCollectorAgent
from agents.qna_retriever import QnARetrieverAgent
from agents.source_discovery import SourceDiscoveryAgent
from agents.verifier import VerificationAgent
from config.settings import QUESTIONS_PER_SLOT, SLOT_CONFIGS
from database.manager import DatabaseManager
from services.notification_engine import NotificationEngine

logger = logging.getLogger("AntigravityHub.QnAOrchestrator")


class QnAOrchestrator:
    """
    Master multi-agent orchestrator coordinating:
    1. JobCollectorAgent (Applied jobs harvesting)
    2. SourceDiscoveryAgent (GitHub & social discovery with SafetyGuard)
    3. QnARetrieverAgent (Authentic Q&A retrieval with exponential backoff)
    4. VerificationAgent (Source grounding & anti-hallucination validation)
    5. CuratorDispatchAgent (Persistence, WebSocket broadcast, and mobile push)
    """

    def __init__(self, db: DatabaseManager, engine: NotificationEngine):
        self.db = db
        self.engine = engine
        self.job_collector = JobCollectorAgent()
        self.source_discovery = SourceDiscoveryAgent()
        self.qna_retriever = QnARetrieverAgent()
        self.verifier = VerificationAgent()
        self.curator_dispatch = CuratorDispatchAgent(db, engine)

    async def run_pipeline_for_slot(
        self,
        slot_id: int,
        force: bool = False,
        target_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs the complete multi-agent pipeline for a specific slot."""
        today_date = target_date or time.strftime("%Y-%m-%d")
        slot_conf = SLOT_CONFIGS.get(slot_id)
        if not slot_conf:
            return {"status": "error", "message": f"Invalid slot_id: {slot_id}"}

        # 1. Guard against duplicate execution for today
        if not force and self.db.is_slot_executed_today(today_date, slot_id):
            logger.info(f"Slot {slot_id} ({slot_conf['name']}) has already completed for {today_date}. Skipping.")
            return {
                "status": "already_executed",
                "slot_id": slot_id,
                "date": today_date,
                "message": "Slot already executed today.",
            }

        logger.info(f"=== Starting Multi-Agent Q&A Pipeline for Slot {slot_id} ({slot_conf['name'].upper()}) ===")

        # Step 1: Collect recent applied jobs
        target_jobs = self.job_collector.collect_recent_applied_jobs(limit=10)

        # Step 2: Discover safe, trending GitHub & community sources
        vetted_sources = self.source_discovery.discover_safe_sources_for_jobs(target_jobs)

        # Step 3: Retrieve authentic question & answer candidates with exponential retries
        raw_candidates = self.qna_retriever.retrieve_candidates_for_slot(
            slot_id=slot_id,
            target_jobs=target_jobs,
            vetted_sources=vetted_sources,
        )

        # Step 4: Rigorous verification & anti-hallucination check
        verified_items = self.verifier.verify_and_structure_candidates(
            candidates=raw_candidates,
            slot_id=slot_id,
            target_date=today_date,
            max_items=QUESTIONS_PER_SLOT,
        )

        if not verified_items:
            logger.warning(f"No candidates passed verification for Slot {slot_id}.")
            return {
                "status": "no_verified_items",
                "slot_id": slot_id,
                "date": today_date,
                "question_count": 0,
            }

        # Step 5: Save to SQLite, broadcast to mobile WebSocket, and dispatch push notification
        count = await self.curator_dispatch.curate_and_dispatch(
            items=verified_items,
            slot_id=slot_id,
            target_date=today_date,
        )

        logger.info(f"=== Multi-Agent Pipeline Completed Successfully for Slot {slot_id}: {count} questions ===")
        return {
            "status": "completed",
            "slot_id": slot_id,
            "slot_name": slot_conf["name"],
            "date": today_date,
            "question_count": count,
            "questions": [q.question for q in verified_items],
        }
