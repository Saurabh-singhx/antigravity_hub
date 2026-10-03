from typing import Optional
from pydantic import BaseModel


class DeviceRegistration(BaseModel):
    device_id: str
    device_name: Optional[str] = "Mobile Device"
    push_token: Optional[str] = None          # Expo Push Token or FCM token
    platform: Optional[str] = "android"       # android / ios / web
