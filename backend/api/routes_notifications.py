import asyncio
import logging
import time
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from database.manager import DatabaseManager
from models.notifications import (
    ActionResponseRequest,
    ActionStatus,
    NotificationPayload,
)
from services.notification_engine import NotificationEngine

logger = logging.getLogger("AntigravityHub.RoutesNotifications")
router = APIRouter(prefix="/api", tags=["Notifications"])


def get_db():
    from app import db
    return db


def get_engine():
    from app import engine
    return engine


@router.post("/notify")
async def send_notification(
    payload: NotificationPayload,
    db: DatabaseManager = Depends(get_db),
    engine: NotificationEngine = Depends(get_engine),
):
    """
    Called by ANY Antigravity CLI workflow (e.g. auto_job_apply)
    to broadcast an event, alert, or milestone to the mobile app.
    """
    if not payload.id:
        payload.id = str(uuid.uuid4())
    if not payload.created_at:
        payload.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    logger.info(f"[{payload.workflow.upper()}] Notification: {payload.title} ({payload.level.value})")

    # 1. Save in local SQLite
    db.save_notification(payload)

    # 2. Real-time broadcast to all connected mobile apps
    await engine.broadcast(payload)

    # 3. Native Expo Push notification dispatch
    tokens = db.get_all_push_tokens()
    if tokens:
        engine.dispatch_expo_push(tokens, payload)

    return {"status": "dispatched", "notification_id": payload.id}


@router.post("/request-action")
async def request_action(
    payload: NotificationPayload,
    db: DatabaseManager = Depends(get_db),
    engine: NotificationEngine = Depends(get_engine),
):
    """
    Called when a workflow needs human input from mobile (e.g., OTP or approval).
    Blocks asynchronously until user responds on their phone or timeout expires!
    """
    if not payload.id:
        payload.id = str(uuid.uuid4())
    if not payload.created_at:
        payload.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not payload.action:
        raise HTTPException(status_code=400, detail="Action details must be specified")

    action = payload.action
    if not action.action_id:
        action.action_id = str(uuid.uuid4())

    logger.info(f"[{payload.workflow}] Action Requested: '{action.prompt}' (ID: {action.action_id})")

    # Save initial pending state
    db.save_notification(payload)
    await engine.broadcast(payload)

    # Push to mobile
    tokens = db.get_all_push_tokens()
    if tokens:
        engine.dispatch_expo_push(tokens, payload)

    # Register Future & wait for mobile response
    future = engine.register_action_future(action.action_id)
    try:
        response_val = await asyncio.wait_for(future, timeout=float(action.timeout_seconds))
        action.status = ActionStatus.RESOLVED
        action.response_value = response_val
        db.resolve_action(action.action_id, response_val)
        return {
            "status": "resolved",
            "action_id": action.action_id,
            "response": response_val,
        }
    except asyncio.TimeoutError:
        action.status = ActionStatus.TIMEOUT
        logger.warning(f"Action '{action.action_id}' timed out after {action.timeout_seconds}s")
        return {
            "status": "timeout",
            "action_id": action.action_id,
            "response": None,
        }
    finally:
        engine.action_futures.pop(action.action_id, None)


@router.post("/actions/{action_id}/respond")
async def respond_to_action(
    action_id: str,
    body: ActionResponseRequest,
    db: DatabaseManager = Depends(get_db),
    engine: NotificationEngine = Depends(get_engine),
):
    """Called by mobile app when user enters an OTP or taps an action button."""
    success = engine.resolve_action(action_id, body.response_value)
    db.resolve_action(action_id, body.response_value)
    logger.info(f"Mobile user responded to action '{action_id}' with: '{body.response_value}'")
    return {"status": "ok", "delivered_to_workflow": success}


@router.get("/notifications")
def get_notifications(
    workflow: Optional[str] = Query(None, description="Filter by workflow (e.g. auto_job_apply)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_db),
):
    """Fetches list of historical notifications for the mobile UI."""
    return db.get_notifications(workflow=workflow, limit=limit, offset=offset)


@router.delete("/notifications")
def clear_notifications(
    scope: str = Query("all", description="all, non_critical, or resolved"),
    older_than_minutes: Optional[int] = Query(None, ge=1),
    db: DatabaseManager = Depends(get_db),
):
    """Cleans up historical notifications."""
    deleted_count = db.clear_notifications(scope=scope, older_than_minutes=older_than_minutes)
    return {"status": "cleared", "deleted_count": deleted_count}


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """Deletes an individual notification."""
    success = db.delete_notification(notification_id)
    return {"status": "deleted" if success else "not_found", "id": notification_id}
