import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket
import requests

from models.notifications import NotificationPayload

logger = logging.getLogger("AntigravityHub.Engine")


class NotificationEngine:
    """
    Real-time notification engine with WebSocket broadcasting,
    synchronous human-in-the-loop action waiting, and Expo push dispatch.
    """

    def __init__(self):
        self.active_websockets: Set[WebSocket] = set()
        # Maps action_id -> asyncio.Future for waiting CLI workflows
        self.action_futures: Dict[str, asyncio.Future] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_websockets.add(websocket)
        logger.info(f"Mobile client connected. Total active clients: {len(self.active_websockets)}")

    def disconnect(self, websocket: WebSocket):
        self.active_websockets.discard(websocket)
        logger.info(f"Mobile client disconnected. Remaining: {len(self.active_websockets)}")

    async def broadcast(self, payload: NotificationPayload):
        """Sends real-time notification to all connected mobile and web clients."""
        data_str = payload.model_dump_json()
        dead_sockets = set()
        for ws in list(self.active_websockets):
            try:
                await ws.send_text(data_str)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                dead_sockets.add(ws)

        for ws in dead_sockets:
            self.disconnect(ws)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcasts arbitrary structured system/qna events to connected mobile clients."""
        message = json.dumps({"event": event_type, "data": data})
        dead_sockets = set()
        for ws in list(self.active_websockets):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"Failed to send event to client: {e}")
                dead_sockets.add(ws)

        for ws in dead_sockets:
            self.disconnect(ws)

    def dispatch_expo_push(self, tokens: List[str], payload: NotificationPayload):
        """Dispatches native push notifications via Expo Push API (works on Android & iOS)."""
        if not tokens:
            return

        messages = []
        for token in tokens:
            if not token.startswith("ExponentPushToken"):
                continue
            priority = "high" if payload.level in ("warning", "error", "critical") else "default"
            msg = {
                "to": token,
                "sound": "default",
                "title": payload.title,
                "body": payload.message,
                "priority": priority,
                "data": {
                    "notification_id": payload.id,
                    "workflow": payload.workflow,
                    "category": payload.category,
                    "action_id": payload.action.action_id if payload.action else None,
                    "action_type": payload.action.action_type.value if payload.action else None,
                },
            }
            messages.append(msg)

        if not messages:
            return

        try:
            res = requests.post(
                "https://exp.host/--/api/v2/push/send",
                headers={
                    "Accept": "application/json",
                    "Accept-encoding": "gzip, deflate",
                    "Content-Type": "application/json",
                },
                json=messages,
                timeout=5,
            )
            logger.info(f"Dispatched {len(messages)} Expo push notifications. Response: {res.status_code}")
        except Exception as e:
            logger.warning(f"Error sending Expo push: {e}")

    def register_action_future(self, action_id: str) -> asyncio.Future:
        """Registers a future so the CLI workflow can await user action from mobile."""
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.action_futures[action_id] = future
        return future

    def resolve_action(self, action_id: str, response_value: str) -> bool:
        """Called when user submits their OTP or action response from mobile."""
        if action_id in self.action_futures:
            future = self.action_futures[action_id]
            if not future.done():
                future.set_result(response_value)
                logger.info(f"Resolved action '{action_id}' with value: '{response_value}'")
                return True
        return False
