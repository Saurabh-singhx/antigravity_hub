import logging
import math
import time
from typing import Any, Dict, List, Optional

from config.settings import SLOT_CONFIGS
from database.manager import DatabaseManager
from models.qna import DailyQnAResponse, PaginatedQnAResponse, QnAItem

logger = logging.getLogger("AntigravityHub.QnAService")


class QnAService:
    """Service layer managing Interview Q&A data queries, pagination, and slot metadata."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_daily_feed(self, date_str: Optional[str] = None) -> DailyQnAResponse:
        """
        Returns today's active questions for the daily mobile feed.
        Includes slot progress so the user sees which slots have completed today.
        """
        today_date = date_str or time.strftime("%Y-%m-%d")
        items = self.db.get_daily_qna(today_date)
        slot_status = self.db.get_today_slot_status(today_date)

        # Determine current active slot based on current hour
        current_hour = time.localtime().tm_hour
        active_slot_id = None
        active_slot_name = None
        for sid, conf in SLOT_CONFIGS.items():
            if conf["start_hour"] <= current_hour < conf["end_hour"]:
                active_slot_id = sid
                active_slot_name = conf["name"]
                break

        return DailyQnAResponse(
            date=today_date,
            active_slot_id=active_slot_id,
            active_slot_name=active_slot_name,
            slot_progress=slot_status,
            items=items,
            total_questions=len(items),
        )

    def get_paginated_history(
        self,
        page: int = 1,
        page_size: int = 10,
        job_filter: Optional[str] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
    ) -> PaginatedQnAResponse:
        """Returns paginated questions from the permanent backend database."""
        page = max(1, page)
        page_size = min(max(1, page_size), 50)
        items, total = self.db.get_qna_history(
            page=page,
            page_size=page_size,
            job_filter=job_filter,
            search=search,
            category=category,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedQnAResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    def toggle_mastered(self, item_id: str, is_mastered: bool) -> bool:
        return self.db.toggle_mastered(item_id, is_mastered)
