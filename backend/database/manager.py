import json
import logging
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from config.settings import DB_PATH
from database.schema import SCHEMA_STATEMENTS
from models.notifications import ActionStatus, NotificationPayload
from models.qna import QnAItem, QnASource, SlotExecution

logger = logging.getLogger("AntigravityHub.DB")


class DatabaseManager:
    """Robust SQLite store for Antigravity notifications, actions, devices, and interview QnA."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            c = conn.cursor()
            for stmt in SCHEMA_STATEMENTS:
                c.execute(stmt)
            conn.commit()

    # =========================================================================
    # NOTIFICATION & ACTION OPERATIONS
    # =========================================================================

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
            conn.commit()

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
            conn.commit()
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

    # =========================================================================
    # INTERVIEW Q&A OPERATIONS
    # =========================================================================

    def save_qna_items(self, items: List[QnAItem]) -> int:
        """Persists a verified batch of interview questions into SQLite."""
        if not items:
            return 0
        inserted = 0
        with self._get_connection() as conn:
            c = conn.cursor()
            for q in items:
                tech_stack_json = json.dumps(q.tech_stack)
                c.execute(
                    """
                    INSERT OR REPLACE INTO qna_questions (
                        id, job_title, company, slot_id, slot_name, date,
                        question, answer, category, tech_stack_json,
                        source_type, source_name, source_url, source_quote,
                        source_stars, reliability_score, verified, difficulty,
                        is_mastered, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        q.id,
                        q.job_title,
                        q.company or "",
                        q.slot_id,
                        q.slot_name,
                        q.date,
                        q.question,
                        q.answer,
                        q.category,
                        tech_stack_json,
                        q.source.source_type,
                        q.source.source_name,
                        q.source.source_url,
                        q.source.source_quote or "",
                        q.source.stars or 0,
                        q.source.reliability_score,
                        1 if q.source.verified else 0,
                        q.difficulty,
                        1 if q.is_mastered else 0,
                        q.created_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    ),
                )
                inserted += 1
            conn.commit()
        return inserted

    def _row_to_qna(self, row: sqlite3.Row) -> QnAItem:
        d = dict(row)
        tech_stack = []
        if d.get("tech_stack_json"):
            try:
                tech_stack = json.loads(d["tech_stack_json"])
            except Exception:
                tech_stack = []

        source = QnASource(
            source_type=d.get("source_type") or "github_repo",
            source_name=d.get("source_name") or "Unknown Source",
            source_url=d.get("source_url") or "",
            source_quote=d.get("source_quote"),
            stars=d.get("source_stars"),
            reliability_score=d.get("reliability_score") or 1.0,
            verified=bool(d.get("verified", 1)),
        )

        return QnAItem(
            id=d["id"],
            job_title=d["job_title"],
            company=d.get("company"),
            slot_id=d["slot_id"],
            slot_name=d["slot_name"],
            date=d["date"],
            question=d["question"],
            answer=d["answer"],
            category=d.get("category") or "Fundamentals",
            tech_stack=tech_stack,
            source=source,
            difficulty=d.get("difficulty") or "Medium",
            is_mastered=bool(d.get("is_mastered", 0)),
            created_at=d.get("created_at"),
        )

    def get_daily_qna(self, date_str: str) -> List[QnAItem]:
        """Fetches questions created for the specified date."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT * FROM qna_questions 
                WHERE date = ? 
                ORDER BY slot_id ASC, created_at ASC
                """,
                (date_str,),
            )
            rows = c.fetchall()
            return [self._row_to_qna(r) for r in rows]

    def get_qna_history(
        self,
        page: int = 1,
        page_size: int = 10,
        job_filter: Optional[str] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Tuple[List[QnAItem], int]:
        """Returns paginated historical questions stored on backend."""
        offset = max(0, (page - 1) * page_size)
        where_clauses = []
        params: List[Any] = []

        if job_filter:
            where_clauses.append("job_title LIKE ?")
            params.append(f"%{job_filter}%")
        if search:
            where_clauses.append("(question LIKE ? OR answer LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if category:
            where_clauses.append("category = ?")
            params.append(category)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self._get_connection() as conn:
            c = conn.cursor()
            # Count total
            c.execute(f"SELECT COUNT(*) FROM qna_questions {where_sql}", params)
            total = c.fetchone()[0]

            # Fetch page items
            query = f"""
                SELECT * FROM qna_questions 
                {where_sql} 
                ORDER BY date DESC, slot_id DESC, created_at DESC 
                LIMIT ? OFFSET ?
            """
            c.execute(query, params + [page_size, offset])
            rows = c.fetchall()
            items = [self._row_to_qna(r) for r in rows]
            return items, total

    def toggle_qna_mastered(self, item_id: str, is_mastered: bool) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE qna_questions SET is_mastered = ? WHERE id = ?",
                (1 if is_mastered else 0, item_id),
            )
            conn.commit()
            return c.rowcount > 0

    # =========================================================================
    # SLOT EXECUTION TRACKING (STRICT 3-PER-DAY CONTROL)
    # =========================================================================

    def record_slot_execution(
        self,
        date_str: str,
        slot_id: int,
        slot_name: str,
        question_count: int,
        status: str = "completed",
        notes: Optional[str] = None,
    ):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT OR REPLACE INTO qna_slot_executions (
                    date, slot_id, slot_name, executed_at, question_count, status, notes
                ) VALUES (?, ?, ?, datetime('now'), ?, ?, ?)
                """,
                (date_str, slot_id, slot_name, question_count, status, notes or ""),
            )
            conn.commit()

    def is_slot_executed_today(self, date_str: str, slot_id: int) -> bool:
        """Checks if a particular slot has already completed today."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT status FROM qna_slot_executions 
                WHERE date = ? AND slot_id = ?
                """,
                (date_str, slot_id),
            )
            row = c.fetchone()
            if not row:
                return False
            # "completed" means it ran
            return row["status"] == "completed"

    def get_today_slot_status(self, date_str: str) -> Dict[str, Dict[str, Any]]:
        """Returns slot execution metadata for the given day."""
        status_map: Dict[str, Dict[str, Any]] = {}
        for sid in (1, 2, 3):
            status_map[str(sid)] = {
                "executed": False,
                "status": "pending",
                "question_count": 0,
                "executed_at": None,
            }

        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT slot_id, status, question_count, executed_at 
                FROM qna_slot_executions 
                WHERE date = ?
                """,
                (date_str,),
            )
            rows = c.fetchall()
            for r in rows:
                sid_str = str(r["slot_id"])
                if sid_str in status_map:
                    status_map[sid_str] = {
                        "executed": r["status"] == "completed",
                        "status": r["status"],
                        "question_count": r["question_count"],
                        "executed_at": r["executed_at"],
                    }
        return status_map
