import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import time
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from agents.orchestrator import QnAOrchestrator
from api.deps import sanitize_filename, verify_hub_token
from api.routes_notifications import router as notifications_router
from api.routes_qna import router as qna_router
from api.routes_system import router as system_router
from config.settings import (
    ACTIVE_PORT_FILE,
    BASE_DIR,
    CORS_ALLOWED_ORIGINS,
    DB_PATH,
    HUB_AUTH_REQUIRED,
    HUB_HOST,
    HUB_PORT,
    SCREENSHOT_MAX_AGE_HOURS,
    SCREENSHOTS_DIR,
    get_or_create_hub_token,
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


def prune_old_screenshots(max_age_hours: int = SCREENSHOT_MAX_AGE_HOURS):
    """Deletes workflow screenshots older than retention window to prevent disk leakage."""
    try:
        now = time.time()
        max_age_sec = max_age_hours * 3600
        pruned = 0
        for f in SCREENSHOTS_DIR.glob("*"):
            if f.is_file() and f.name != ".gitkeep":
                if now - f.stat().st_mtime > max_age_sec:
                    f.unlink(missing_ok=True)
                    pruned += 1
        if pruned > 0:
            logger.info(f"🧹 Pruned {pruned} screenshots older than {max_age_hours}h.")
    except Exception as e:
        logger.debug(f"Error during screenshot pruning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: starts background boot-up slot scheduler and graceful teardown."""
    logger.info("Initializing Antigravity Hub services...")
    # Prune old screenshots on boot
    prune_old_screenshots()
    # Log auth token status
    token = get_or_create_hub_token()
    logger.info(f"🔒 Antigravity Hub Security: Token Auth is {'ENABLED' if HUB_AUTH_REQUIRED else 'DISABLED'}")
    logger.info(f"🔑 Antigravity Hub Token: {token}")

    # Start 3-times-a-day background scheduler
    scheduler.start()
    yield
    logger.info("Shutting down Antigravity Hub services...")
    scheduler.stop()


app = FastAPI(
    title="Antigravity Hub • Local Notification & Interview Prep Relay",
    description="Centralized local relay connecting Antigravity CLI workflows and autonomous interview preparation to mobile.",
    version="2.1.0",
    lifespan=lifespan,
)

# Tightened CORS: allows local dev bundlers and LAN origins for mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(system_router)
app.include_router(notifications_router)
app.include_router(qna_router)


# Authenticated & Sanitized Screenshot Endpoints
@app.get("/api/screenshots/{filename}")
@app.get("/screenshots/{filename}")
def get_screenshot(
    filename: str,
    _token: str = Depends(verify_hub_token),
):
    """
    Serves captured workflow screenshots with strict path-traversal
    validation and token authentication.
    """
    safe_name = sanitize_filename(filename)
    file_path = SCREENSHOTS_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path=str(file_path))


@app.post("/api/screenshots/upload")
async def upload_screenshots(
    request: Request,
    _token: str = Depends(verify_hub_token),
):
    """
    Upload one or multiple screenshots from mobile app or web client.
    Supports both multipart/form-data and application/json (base64).
    Saves to SCREENSHOTS_DIR and returns public URLs with token.
    """
    saved_files = []
    content_type = request.headers.get("content-type", "")

    active_token = get_or_create_hub_token()
    token_param = f"?token={active_token}" if active_token else ""

    # Determine LAN IP for mobile reachability
    lan_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    port = 8765
    if ACTIVE_PORT_FILE.exists():
        try:
            p = ACTIVE_PORT_FILE.read_text().strip()
            if p.isdigit():
                port = int(p)
        except Exception:
            pass

    if "multipart/form-data" in content_type:
        form = await request.form()
        files_to_process = form.getlist("files") or form.getlist("images") or form.getlist("file") or form.getlist("image")
        if not files_to_process:
            for k, val in form.items():
                if hasattr(val, "filename"):
                    files_to_process.append(val)

        for upload in files_to_process:
            if hasattr(upload, "filename") and upload.filename:
                orig_name = Path(upload.filename).name
                ext = Path(orig_name).suffix.lower()
                if ext not in (".png", ".jpg", ".jpeg", ".webp"):
                    ext = ".png"
                clean_stem = "".join(c for c in Path(orig_name).stem if c.isalnum() or c in ("-", "_"))[:32] or "screenshot"
                filename = f"{int(time.time()*1000)}_{clean_stem}{ext}"
                dest = SCREENSHOTS_DIR / filename
                content = await upload.read()
                dest.write_bytes(content)
                url = f"http://{lan_ip}:{port}/api/screenshots/{filename}{token_param}"
                saved_files.append({
                    "filename": filename,
                    "url": url,
                    "path": str(dest.resolve()),
                    "size": len(content),
                })
    else:
        # JSON body with base64 images
        try:
            body = await request.json()
            images = body.get("images") or body.get("screenshots") or []
            if isinstance(images, str):
                images = [images]
            import base64
            for idx, img_data in enumerate(images):
                if not img_data:
                    continue
                if "base64," in img_data:
                    img_data = img_data.split("base64,")[1]
                raw_bytes = base64.b64decode(img_data)
                filename = f"{int(time.time()*1000)}_upload_{idx+1}.png"
                dest = SCREENSHOTS_DIR / filename
                dest.write_bytes(raw_bytes)
                url = f"http://{lan_ip}:{port}/api/screenshots/{filename}{token_param}"
                saved_files.append({
                    "filename": filename,
                    "url": url,
                    "path": str(dest.resolve()),
                    "size": len(raw_bytes),
                })
        except Exception as e:
            logger.warning(f"Error parsing upload payload: {e}")

    if not saved_files:
        raise HTTPException(status_code=400, detail="No valid screenshot images found in request")

    logger.info(f"📸 Saved {len(saved_files)} uploaded screenshot(s) to {SCREENSHOTS_DIR}")
    return {
        "status": "ok",
        "count": len(saved_files),
        "files": saved_files,
        "screenshot_paths": [f["path"] for f in saved_files],
        "screenshot_urls": [f["url"] for f in saved_files],
    }



# Real-time WebSocket Endpoint (Protected with Hub Token)
@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket connection for live mobile app updates. Protected by Hub Token."""
    token = websocket.query_params.get("token") or websocket.headers.get("x-hub-token")
    if HUB_AUTH_REQUIRED:
        expected = get_or_create_hub_token()
        if not token or not secrets.compare_digest(token.strip(), expected):
            client_host = websocket.client.host if websocket.client else "unknown"
            logger.warning(f"Rejecting unauthorized WebSocket connection from {client_host}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

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
                    act_secret = msg.get("action_secret")
                    if act_id and val is not None:
                        if engine.verify_action_secret(act_id, act_secret):
                            engine.resolve_action(act_id, str(val))
                            db.resolve_action(act_id, str(val))
                        else:
                            logger.warning(f"WebSocket action response rejected: invalid action_secret for '{act_id}'")
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
