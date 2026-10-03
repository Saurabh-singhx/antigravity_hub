import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from agents.orchestrator import QnAOrchestrator
from api.deps import require_rate_limit, verify_hub_token
from core.time_slots import TimeSlotEngine
from database.manager import DatabaseManager
from models.qna import (
    DailyQnAResponse,
    PaginatedQnAResponse,
    QnAManualTriggerRequest,
)
from services.qna_service import QnAService

logger = logging.getLogger("AntigravityHub.RoutesQnA")
router = APIRouter(prefix="/api/qna", tags=["Interview Prep QnA"], dependencies=[Depends(verify_hub_token)])


def get_db():
    from app import db
    return db


def get_qna_service():
    from app import qna_service
    return qna_service


def get_orchestrator():
    from app import orchestrator
    return orchestrator


@router.get("/daily", response_model=DailyQnAResponse)
def get_daily_qna(
    date: Optional[str] = Query(None, description="Optional YYYY-MM-DD date (defaults to today)"),
    qna_service: QnAService = Depends(get_qna_service),
):
    """
    Returns today's active interview questions for the primary mobile view.
    Automatically excludes previous days so the mobile feed stays clean and fresh.
    """
    return qna_service.get_daily_feed(date)


@router.get("/history", response_model=PaginatedQnAResponse)
def get_qna_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    job: Optional[str] = Query(None, description="Filter by job title (e.g. Flutter, React, Python)"),
    search: Optional[str] = Query(None, description="Search questions and answers"),
    category: Optional[str] = Query(None, description="Filter by category (Fundamentals, System Design, etc.)"),
    qna_service: QnAService = Depends(get_qna_service),
):
    """
    Returns paginated interview questions permanently retained on the backend.
    Allows user to browse past questions, filter by tech stack or search keywords.
    """
    return qna_service.get_paginated_history(
        page=page,
        page_size=page_size,
        job_filter=job,
        search=search,
        category=category,
    )


@router.get("/slots/status")
def get_slots_status(
    date: Optional[str] = Query(None),
    db: DatabaseManager = Depends(get_db),
):
    """Returns today's execution status for the 3 daily slots."""
    today = date or time.strftime("%Y-%m-%d")
    current_slot = TimeSlotEngine.get_current_slot()
    slot_status = db.get_today_slot_status(today)
    return {
        "date": today,
        "active_slot": current_slot,
        "slots": slot_status,
    }


@router.post(
    "/trigger",
    dependencies=[Depends(require_rate_limit(max_requests=5, window_seconds=60, key_prefix="qna_trigger"))],
)
async def trigger_slot_manually(
    req: QnAManualTriggerRequest,
    orchestrator: QnAOrchestrator = Depends(get_orchestrator),
):
    """
    Manually triggers the multi-agent pipeline for a specific slot or active slot.
    Useful for testing or requesting immediate interview prep.
    """
    slot_id = req.slot_id
    if slot_id is None:
        slot_id = TimeSlotEngine.get_current_slot()
        if slot_id is None:
            # Default to slot 1 if triggered during quiet hours
            slot_id = 1

    result = await orchestrator.run_pipeline_for_slot(slot_id=slot_id, force=req.force)
    return result


@router.post("/{item_id}/mastered")
def toggle_question_mastered(
    item_id: str,
    mastered: bool = Query(True),
    qna_service: QnAService = Depends(get_qna_service),
):
    """Allows user to mark a question as mastered or for review."""
    success = qna_service.toggle_mastered(item_id, mastered)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"status": "updated", "id": item_id, "is_mastered": mastered}
