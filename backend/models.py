from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NotificationLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActionType(str, Enum):
    NONE = "none"
    CONFIRM = "confirm"      # Approve / Reject buttons
    INPUT = "input"          # Text input field (e.g., OTP, 2FA code, prompt answer)
    CHOICE = "choice"        # Multi-option picker


class ActionStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class NotificationAction(BaseModel):
    action_id: str
    action_type: ActionType = ActionType.NONE
    prompt: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    timeout_seconds: int = 120
    status: ActionStatus = ActionStatus.PENDING
    response_value: Optional[str] = None
    resolved_at: Optional[str] = None


class NotificationPayload(BaseModel):
    id: Optional[str] = None
    workflow: str = "general"                 # "auto_job_apply", "coding_agent", etc.
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    category: str = "general"                 # "job_applied", "captcha", "otp", "milestone", "error"
    action: Optional[NotificationAction] = None
    screenshot_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class ActionResponseRequest(BaseModel):
    action_id: str
    response_value: str                       # e.g., "684920" (OTP) or "APPROVE" or "SKIP"


class DeviceRegistration(BaseModel):
    device_id: str
    device_name: Optional[str] = "Mobile Device"
    push_token: Optional[str] = None          # Expo Push Token or FCM token
    platform: Optional[str] = "android"       # android / ios / web
