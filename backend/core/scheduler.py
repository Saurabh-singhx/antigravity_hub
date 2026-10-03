import asyncio
import datetime
import logging
from typing import Optional

from agents.orchestrator import QnAOrchestrator
from config.settings import SLOT_CONFIGS
from core.time_slots import TimeSlotEngine
from database.manager import DatabaseManager

logger = logging.getLogger("AntigravityHub.Scheduler")


class BackgroundScheduler:
    """
    Background scheduler running on computer boot and continuously while active.
    Enforces strict 3-times-a-day schedule:
    - Runs active slot upon boot
    - Skips past slots if computer was off/opened late
    - Checks every 5 minutes for new active slot boundaries
    """

    def __init__(self, orchestrator: QnAOrchestrator, db: DatabaseManager):
        self.orchestrator = orchestrator
        self.db = db
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def check_and_trigger_active_slot(self) -> None:
        """
        Evaluates current time, marks overdue slots as skipped,
        and triggers the currently active slot if it has not yet run today.
        """
        now = datetime.datetime.now()
        today_date = now.strftime("%Y-%m-%d")

        # 1. Check and mark passed slots as skipped if they were never run
        passed_slots = TimeSlotEngine.get_passed_slots(now)
        for sid in passed_slots:
            slot_name = SLOT_CONFIGS[sid]["name"]
            if not self.db.is_slot_executed_today(today_date, sid):
                # Check if it was already recorded
                today_status = self.db.get_today_slot_status(today_date)
                if today_status.get(str(sid), {}).get("status") == "pending":
                    logger.info(f"Slot {sid} ({slot_name}) window has passed. Marking as SKIPPED per schedule rules.")
                    self.db.record_slot_execution(
                        date_str=today_date,
                        slot_id=sid,
                        slot_name=slot_name,
                        question_count=0,
                        status="skipped",
                        notes=f"Computer was off during slot window ({SLOT_CONFIGS[sid]['start_hour']}:00 - {SLOT_CONFIGS[sid]['end_hour']}:00). Skipped.",
                    )

        # 2. Check active slot for right now
        active_slot = TimeSlotEngine.get_current_slot(now)
        if active_slot is None:
            logger.info("Current time is in quiet period (00:00 - 04:00). No slot to execute.")
            return

        slot_name = SLOT_CONFIGS[active_slot]["name"]
        if self.db.is_slot_executed_today(today_date, active_slot):
            logger.info(f"Slot {active_slot} ({slot_name}) has already completed for today ({today_date}).")
            return

        logger.info(f"Active slot window detected: Slot {active_slot} ({slot_name}). Executing pipeline...")
        try:
            await self.orchestrator.run_pipeline_for_slot(slot_id=active_slot, force=False)
        except Exception as e:
            logger.error(f"Error executing pipeline for Slot {active_slot}: {e}", exc_info=True)

    async def _loop(self):
        logger.info("BackgroundScheduler loop started.")
        # Initial boot check after 4s warm-up
        await asyncio.sleep(4)
        await self.check_and_trigger_active_slot()

        # Check every 5 minutes (300s)
        while self._running:
            try:
                await asyncio.sleep(300)
                if not self._running:
                    break
                await self.check_and_trigger_active_slot()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)

    def start(self):
        if not self._running:
            self._running = True
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._loop())
            logger.info("BackgroundScheduler registered and launched.")

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("BackgroundScheduler stopped.")
