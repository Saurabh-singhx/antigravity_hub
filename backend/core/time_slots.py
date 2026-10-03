import datetime
import logging
from typing import Dict, List, Optional, Tuple

from config.settings import SLOT_CONFIGS

logger = logging.getLogger("AntigravityHub.TimeSlots")


class TimeSlotEngine:
    """
    Manages daily time slots and enforce strict 3-times-a-day schedule:
    Slot 1 (Morning): 04:00 - 11:00 (4:00 AM - 10:59 AM)
    Slot 2 (Afternoon): 11:00 - 17:00 (11:00 AM - 4:59 PM)
    Slot 3 (Evening): 17:00 - 24:00 (5:00 PM - 11:59 PM)
    Quiet (Night): 00:00 - 04:00 (No scheduled runs)
    """

    @classmethod
    def get_current_slot(cls, dt: Optional[datetime.datetime] = None) -> Optional[int]:
        """
        Determines which slot is ACTIVE right now.
        Returns slot_id (1, 2, or 3), or None if during quiet hours (00:00 - 04:00).
        """
        now = dt or datetime.datetime.now()
        current_hour = now.hour

        for sid, conf in SLOT_CONFIGS.items():
            if conf["start_hour"] <= current_hour < conf["end_hour"]:
                return sid

        return None

    @classmethod
    def get_passed_slots(cls, dt: Optional[datetime.datetime] = None) -> List[int]:
        """
        Returns list of slot IDs whose time window has already passed today.
        These MUST BE SKIPPED and never run if the PC was opened after their window closed.
        """
        now = dt or datetime.datetime.now()
        current_hour = now.hour
        passed = []

        for sid, conf in SLOT_CONFIGS.items():
            if conf["end_hour"] <= current_hour:
                passed.append(sid)

        return passed

    @classmethod
    def get_slot_info(cls, slot_id: int) -> Optional[Dict]:
        return SLOT_CONFIGS.get(slot_id)
