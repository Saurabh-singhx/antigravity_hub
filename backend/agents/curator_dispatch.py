import logging
import time
from typing import List

from config.settings import SLOT_CONFIGS
from database.manager import DatabaseManager
from models.notifications import NotificationLevel, NotificationPayload
from models.qna import QnAItem
from services.notification_engine import NotificationEngine

logger = logging.getLogger("AntigravityHub.CuratorDispatchAgent")


class CuratorDispatchAgent:
    """
    Agent responsible for persisting verified Q&A sets, updating slot execution metadata,
    and dispatching real-time notifications to the mobile app over WebSocket and Expo push.
    """

    def __init__(self, db: DatabaseManager, engine: NotificationEngine):
        self.db = db
        self.engine = engine

    async def curate_and_dispatch(
        self,
        items: List[QnAItem],
        slot_id: int,
        target_date: str,
    ) -> int:
        """Saves questions and dispatches them to mobile."""
        if not items:
            logger.warning(f"No items to dispatch for Slot {slot_id}.")
            return 0

        # 1. Save items into backend database
        inserted_count = self.db.save_qna_items(items)

        # 2. Record completed slot execution in DB
        slot_conf = SLOT_CONFIGS.get(slot_id, {})
        slot_name = slot_conf.get("name", f"slot_{slot_id}")
        self.db.record_slot_execution(
            date_str=target_date,
            slot_id=slot_id,
            slot_name=slot_name,
            question_count=inserted_count,
            status="completed",
            notes=f"Generated {inserted_count} questions based on verified sources.",
        )

        # 3. Create notification payload for mobile
        slot_title = slot_conf.get("title", f"Slot {slot_id} Prep")
        top_tech = items[0].tech_stack[0] if items and items[0].tech_stack else "Tech Stack"
        sample_q = items[0].question[:70] + "..." if len(items[0].question) > 70 else items[0].question

        notif_title = f"{slot_title}: {len(items)} New Questions"
        notif_body = f"Top question: \"{sample_q}\"\nSourced from {items[0].source.source_name}."

        payload = NotificationPayload(
            workflow="interview_prep",
            title=notif_title,
            message=notif_body,
            level=NotificationLevel.INFO,
            category="interview_qna",
            metadata={
                "slot_id": slot_id,
                "slot_name": slot_name,
                "date": target_date,
                "question_count": len(items),
                "source": items[0].source.source_name,
            },
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # 4. Save to notifications table & broadcast via WebSocket
        self.db.save_notification(payload)
        await self.engine.broadcast(payload)

        # 5. Broadcast structured qna_update event so mobile updates list dynamically
        await self.engine.broadcast_event("qna_updated", {
            "slot_id": slot_id,
            "date": target_date,
            "count": len(items),
        })

        # 6. Dispatch native Expo Push Notification
        tokens = self.db.get_all_push_tokens()
        if tokens:
            self.engine.dispatch_expo_push(tokens, payload)

        logger.info(f"CuratorDispatchAgent dispatched Slot {slot_id} ({len(items)} questions) to mobile.")
        return inserted_count
