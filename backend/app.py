import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import socket
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agents.orchestrator import QnAOrchestrator
from api.routes_notifications import router as notifications_router
from api.routes_qna import router as qna_router
from api.routes_system import router as system_router
from config.settings import (
    ACTIVE_PORT_FILE,
    BASE_DIR,
    DB_PATH,
    HUB_HOST,
    HUB_PORT,
    SCREENSHOTS_DIR,
)
from core.scheduler import BackgroundScheduler
from database.manager import DatabaseManager
from services.notification_engine import NotificationEngine
from services.qna_service import QnAService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AntigravityHub.Server")

# Initialize Storage & Core Engines
db = DatabaseManager(DB_PATH)
engine = NotificationEngine()
qna_service = QnAService(db)
orchestrator = QnAOrchestrator(db, engine)
scheduler = BackgroundScheduler(orchestrator, db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: starts background boot-up slot scheduler and graceful teardown."""
    logger.info("Initializing Antigravity Hub services...")
    # Start 3-times-a-day background scheduler
    scheduler.start()
    yield
    logger.info("Shutting down Antigravity Hub services...")
    scheduler.stop()


app = FastAPI(
    title="Antigravity Hub • Local Notification & Interview Prep Relay",
    description="Centralized local relay connecting Antigravity CLI workflows and autonomous interview preparation to mobile.",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for React Native and Expo web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Screenshots Mount
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

# Mount Routers
app.include_router(system_router)
app.include_router(notifications_router)
app.include_router(qna_router)


# Real-time WebSocket Endpoint
@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket connection for live mobile app updates."""
    await engine.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # Handle mobile action response
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

    desired_port = int(os.environ.get("HUB_PORT", HUB_PORT))
    host = os.environ.get("HUB_HOST", HUB_HOST)

    port = find_available_port(desired_port)
    if port != desired_port:
        logger.warning(f"Port {desired_port} was already in use. Switched to available port: {port}")

    # Persist the active port so client SDK and mobile know where to connect
    ACTIVE_PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_PORT_FILE.write_text(str(port))

    logger.info(f"Starting Antigravity Hub on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=False)
