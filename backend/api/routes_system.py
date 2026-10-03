import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.deps import verify_hub_token
from config.settings import BASE_DIR, DB_PATH, HUB_AUTH_REQUIRED
from core.time_slots import TimeSlotEngine
from database.manager import DatabaseManager
from models.devices import DeviceRegistration
from services.notification_engine import NotificationEngine

router = APIRouter(tags=["System"])


def get_db():
    from app import db
    return db


def get_engine():
    from app import engine
    return engine


@router.get("/")
def index(engine: NotificationEngine = Depends(get_engine)):
    return {
        "service": "Antigravity Hub • Local Relay & Interview Prep Engine",
        "status": "online",
        "auth_required": HUB_AUTH_REQUIRED,
        "active_clients": len(engine.active_websockets),
        "docs": "/docs",
        "download_apk": "/download",
    }


@router.get("/download")
@router.get("/apk")
@router.head("/download")
@router.head("/apk")
def download_apk():
    """Serves the compiled Android APK directly to mobile phones over Wi-Fi."""
    apk_path = BASE_DIR.parent / "AntigravityHub.apk"
    if apk_path.exists():
        return FileResponse(
            path=str(apk_path),
            filename="AntigravityHub.apk",
            media_type="application/vnd.android.package-archive",
        )
    raise HTTPException(status_code=404, detail="APK not found")


@router.get("/api/status")
def get_status(
    db: DatabaseManager = Depends(get_db),
    engine: NotificationEngine = Depends(get_engine),
):
    today = time.strftime("%Y-%m-%d")
    current_slot = TimeSlotEngine.get_current_slot()
    return {
        "status": "online",
        "auth_required": HUB_AUTH_REQUIRED,
        "active_connections": len(engine.active_websockets),
        "db_path": db.db_path,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "active_slot": current_slot,
        "today_slots": db.get_today_slot_status(today),
    }


@router.get("/api/auth/verify")
def verify_auth(_token: str = Depends(verify_hub_token)):
    """Used by mobile app settings modal to test and verify if token is valid."""
    return {"status": "authenticated", "auth_required": HUB_AUTH_REQUIRED}


@router.post("/api/devices/register")
def register_device(
    device: DeviceRegistration,
    _token: str = Depends(verify_hub_token),
    db: DatabaseManager = Depends(get_db),
):
    """Registers mobile phone device and push token. Protected by Hub Token."""
    db.register_device(
        device_id=device.device_id,
        device_name=device.device_name or "Mobile App",
        push_token=device.push_token or "",
        platform=device.platform or "android",
    )
    return {"status": "registered"}
