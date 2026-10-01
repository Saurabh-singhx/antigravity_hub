import json
import logging
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional
from models import ActionStatus, NotificationPayload

logger = logging.getLogger("AntigravityHub.DB")


class DatabaseManager:
    """SQLite store for all Antigravity workflow notifications, actions, and devices."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            root = Path(__file__).resolve().parent
            data_dir = root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "hub.db")
        else:
            self.db_path = db_path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    workflow TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action_id TEXT,
                    action_type TEXT,
                    action_prompt TEXT,
                    action_options TEXT,
                    action_status TEXT,
                    action_response TEXT,
                    screenshot_url TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS device_tokens (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT,
                    push_token TEXT,
                    platform TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workflow_created 
                ON notifications(workflow, created_at DESC)
                """
            )

    def save_notification(self, payload: NotificationPayload):
        with self._get_connection() as conn:
            c = conn.cursor()
            action_id = payload.action.action_id if payload.action else None
            action_type = payload.action.action_type.value if payload.action else None
            action_prompt = payload.action.prompt if payload.action else None
            action_options = json.dumps(payload.action.options) if payload.action else None
            action_status = payload.action.status.value if payload.action else None
            action_response = payload.action.response_value if payload.action else None

            created_at_val = payload.created_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            c.execute(
                """
                INSERT OR REPLACE INTO notifications (
                    id, workflow, title, message, level, category,
                    action_id, action_type, action_prompt, action_options,
                    action_status, action_response, screenshot_url, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.id,
                    payload.workflow,
                    payload.title,
                    payload.message,
                    payload.level.value,
                    payload.category,
                    action_id,
                    action_type,
                    action_prompt,
                    action_options,
                    action_status,
                    action_response,
                    payload.screenshot_url,
                    json.dumps(payload.metadata),
                    created_at_val,
                ),
            )

    def get_notifications(
        self,
        workflow: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            if workflow:
                c.execute(
                    """
                    SELECT * FROM notifications 
                    WHERE workflow = ? 
                    ORDER BY created_at DESC LIMIT ? OFFSET ?
                    """,
                    (workflow, limit, offset),
                )
            else:
                c.execute(
                    """
                    SELECT * FROM notifications 
                    ORDER BY created_at DESC LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
            rows = c.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("metadata_json"):
                    try:
                        item["metadata"] = json.loads(item["metadata_json"])
                    except Exception:
                        item["metadata"] = {}
                else:
                    item["metadata"] = {}
                if item.get("action_options"):
                    try:
                        item["action_options"] = json.loads(item["action_options"])
                    except Exception:
                        item["action_options"] = []
                results.append(item)
            return results

    def resolve_action(self, action_id: str, response_value: str) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                UPDATE notifications 
                SET action_status = ?, action_response = ? 
                WHERE action_id = ?
                """,
                (ActionStatus.RESOLVED.value, response_value, action_id),
            )
            return c.rowcount > 0

    def register_device(self, device_id: str, device_name: str, push_token: str, platform: str):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO device_tokens (device_id, device_name, push_token, platform, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(device_id) DO UPDATE SET
                    device_name = excluded.device_name,
                    push_token = CASE WHEN excluded.push_token != '' AND excluded.push_token IS NOT NULL THEN excluded.push_token ELSE device_tokens.push_token END,
                    platform = excluded.platform,
                    updated_at = datetime('now')
                """,
                (device_id, device_name, push_token or "", platform),
            )
            conn.commit()

    def get_all_push_tokens(self) -> List[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT push_token FROM device_tokens WHERE push_token IS NOT NULL AND push_token != ''")
            return [r[0] for r in c.fetchall()]

    def delete_notification(self, notification_id: str) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
            conn.commit()
            return c.rowcount > 0

    def clear_notifications(self, scope: str = "all", older_than_minutes: Optional[int] = None) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            if older_than_minutes and older_than_minutes > 0:
                time_threshold = f"-{older_than_minutes} minutes"
                if scope == "all":
                    c.execute(
                        """
                        DELETE FROM notifications 
                        WHERE (action_status IS NULL OR action_status != 'pending')
                          AND datetime(created_at) <= datetime('now', ?)
                        """,
                        (time_threshold,),
                    )
                elif scope == "resolved":
                    c.execute(
                        """
                        DELETE FROM notifications 
                        WHERE (action_status = 'resolved' OR (action_id IS NULL AND level NOT IN ('critical', 'error')))
                          AND datetime(created_at) <= datetime('now', ?)
                        """,
                        (time_threshold,),
                    )
                else:  # "non_critical"
                    c.execute(
                        """
                        DELETE FROM notifications 
                        WHERE (level NOT IN ('critical', 'error')) 
                          AND (action_status IS NULL OR action_status != 'pending')
                          AND datetime(created_at) <= datetime('now', ?)
                        """,
                        (time_threshold,),
                    )
            elif scope == "non_critical":
                c.execute(
                    """
                    DELETE FROM notifications 
                    WHERE (level NOT IN ('critical', 'error')) 
                      AND (action_status IS NULL OR action_status != 'pending')
                    """
                )
            elif scope == "resolved":
                c.execute(
                    """
                    DELETE FROM notifications 
                    WHERE action_status = 'resolved' OR (action_id IS NULL AND level NOT IN ('critical', 'error'))
                    """
                )
            else:  # "all"
                c.execute("DELETE FROM notifications")
            conn.commit()
            return c.rowcount
