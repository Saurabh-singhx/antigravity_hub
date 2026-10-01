import asyncio
import json
import logging
import os
from pathlib import Path
import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from db import DatabaseManager
from models import (
    ActionResponseRequest,
    ActionStatus,
    DeviceRegistration,
    NotificationAction,
    NotificationLevel,
    NotificationPayload,
)
from notification_engine import NotificationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AntigravityHub.Server")

app = FastAPI(
    title="Antigravity Hub • Local Notification & Remote Control Relay",
    description="Centralized local relay connecting any Antigravity CLI workflow to your mobile app.",
    version="1.0.0",
)

# Enable CORS for React Native and Expo web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Storage & Engine
root_dir = Path(__file__).resolve().parent
screenshots_dir = root_dir / "data" / "screenshots"
screenshots_dir.mkdir(parents=True, exist_ok=True)

app.mount("/screenshots", StaticFiles(directory=str(screenshots_dir)), name="screenshots")

db = DatabaseManager()
engine = NotificationEngine()


@app.get("/")
def index():
    return {
        "service": "Antigravity Hub Local Relay",
        "status": "online",
        "active_clients": len(engine.active_websockets),
        "docs": "/docs",
        "download_apk": "/download",
    }


@app.get("/download")
@app.get("/apk")
def download_apk():
    """Serves the latest compiled Android APK directly to mobile phones over Wi-Fi."""
    apk_path = root_dir.parent / "AntigravityHub.apk"
    if apk_path.exists():
        return FileResponse(
            path=str(apk_path),
            filename="AntigravityHub.apk",
            media_type="application/vnd.android.package-archive",
        )
    raise HTTPException(status_code=404, detail="APK not found")


@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "active_connections": len(engine.active_websockets),
        "db_path": db.db_path,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.post("/api/notify")
async def send_notification(payload: NotificationPayload):
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


@app.post("/api/request-action")
async def request_action(payload: NotificationPayload):
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


@app.post("/api/actions/{action_id}/respond")
async def respond_to_action(action_id: str, body: ActionResponseRequest):
    """Called by mobile app when user enters an OTP or taps an action button."""
    success = engine.resolve_action(action_id, body.response_value)
    db.resolve_action(action_id, body.response_value)
    logger.info(f"Mobile user responded to action '{action_id}' with: '{body.response_value}'")
    return {"status": "ok", "delivered_to_workflow": success}


@app.get("/api/notifications")
def get_notifications(
    workflow: Optional[str] = Query(None, description="Filter by workflow (e.g. auto_job_apply)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Fetches list of historical notifications for the mobile UI."""
    return db.get_notifications(workflow=workflow, limit=limit, offset=offset)


@app.delete("/api/notifications")
def clear_notifications(
    scope: str = Query("all", description="all, non_critical, or resolved"),
    older_than_minutes: Optional[int] = Query(None, ge=1),
):
    """Cleans up historical notifications."""
    deleted_count = db.clear_notifications(scope=scope, older_than_minutes=older_than_minutes)
    logger.info(f"Cleared {deleted_count} notifications (scope={scope}, older_than_minutes={older_than_minutes})")
    return {"status": "cleared", "deleted_count": deleted_count}


@app.delete("/api/notifications/{notification_id}")
def delete_notification(notification_id: str):
    """Deletes an individual notification."""
    success = db.delete_notification(notification_id)
    return {"status": "deleted" if success else "not_found", "id": notification_id}


@app.post("/api/devices/register")
def register_device(device: DeviceRegistration):
    """Registers mobile phone device and push token."""
    db.register_device(
        device_id=device.device_id,
        device_name=device.device_name or "Mobile App",
        push_token=device.push_token or "",
        platform=device.platform or "android",
    )
    logger.info(f"Registered mobile device: {device.device_name} ({device.platform})")
    return {"status": "registered"}


@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket connection for live mobile app updates."""
    await engine.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any incoming heartbeats or client commands
            try:
                msg = json.loads(data)
                if msg.get("type") == "action_response":
                    act_id = msg.get("action_id")
                    val = msg.get("value")
                    if act_id and val is not None:
                        engine.resolve_action(act_id, str(val))
                        db.resolve_action(act_id, str(val))
            except Exception:
                pass
    except WebSocketDisconnect:
        engine.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket closed: {e}")
        engine.disconnect(websocket)


import socket


def find_available_port(start_port: int = 8765, max_tries: int = 15) -> int:
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", p))
                return p
            except OSError:
                continue
    return start_port


if __name__ == "__main__":
    import uvicorn

    desired_port = int(os.environ.get("HUB_PORT", 8765))
    host = os.environ.get("HUB_HOST", "0.0.0.0")

    port = find_available_port(desired_port)
    if port != desired_port:
        logger.warning(f"Port {desired_port} was already in use. Switched to available port: {port}")

    # Persist the active port so client SDK and mobile know where to connect
    port_file = root_dir / "data" / "active_port.txt"
    port_file.parent.mkdir(parents=True, exist_ok=True)
    port_file.write_text(str(port))

    logger.info(f"Starting Antigravity Hub on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=False)

