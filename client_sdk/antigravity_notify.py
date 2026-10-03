import json
import logging
import os
from pathlib import Path
import shutil
import time
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger("AntigravityNotify")


class AntigravityNotifier:
    """
    Universal Client SDK for sending notifications and requesting human actions
    from ANY Antigravity CLI workflow, coding agent, or automation script to the mobile app.
    Automatically discovers active port and authenticates using .hub_secret.
    """

    def __init__(self, hub_url: Optional[str] = None, token: Optional[str] = None):
        backend_dir = Path(__file__).resolve().parent.parent / "backend"
        data_dir = backend_dir / "data"

        # Hub URL Discovery
        if not hub_url:
            env_url = os.environ.get("ANTIGRAVITY_HUB_URL")
            if env_url:
                self.hub_url = env_url.rstrip("/")
            else:
                port_file = data_dir / "active_port.txt"
                if port_file.exists():
                    try:
                        p = port_file.read_text().strip()
                        self.hub_url = f"http://localhost:{p}"
                    except Exception:
                        self.hub_url = "http://localhost:8765"
                else:
                    self.hub_url = "http://localhost:8765"
        else:
            self.hub_url = hub_url.rstrip("/")

        # Security Token Discovery
        self.token = token or os.environ.get("ANTIGRAVITY_HUB_TOKEN") or os.environ.get("HUB_API_KEY")
        if not self.token:
            secret_file = data_dir / ".hub_secret"
            if secret_file.exists():
                try:
                    self.token = secret_file.read_text().strip()
                except Exception:
                    self.token = ""
            else:
                self.token = ""

        self.session = requests.Session()
        if self.token:
            self.session.headers.update({
                "X-Hub-Token": self.token,
                "Authorization": f"Bearer {self.token}",
            })

        self.screenshots_dir = data_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def is_hub_online(self) -> bool:
        """Checks if local Antigravity Hub backend is running."""
        try:
            r = self.session.get(f"{self.hub_url}/api/status", timeout=0.8)
            return r.status_code == 200
        except Exception:
            return False

    def ensure_hub_running(self) -> bool:
        """
        Automatically spins up the local backend on-demand if it is not already running.
        Zero background resource consumption when your workflows are idle!
        """
        if self.is_hub_online():
            return True

        logger.info("[AntigravityNotify] Hub backend is not running. Launching on-demand...")
        backend_dir = Path(__file__).resolve().parent.parent / "backend"
        venv_python = backend_dir / ".venv" / "bin" / "python"
        import sys, subprocess
        python_bin = str(venv_python) if venv_python.exists() else sys.executable
        app_file = str(backend_dir / "app.py")

        try:
            subprocess.Popen(
                [python_bin, app_file],
                cwd=str(backend_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Wait up to 4s for startup
            for _ in range(8):
                time.sleep(0.4)
                port_file = backend_dir / "data" / "active_port.txt"
                if port_file.exists():
                    try:
                        p = port_file.read_text().strip()
                        self.hub_url = f"http://localhost:{p}"
                    except Exception:
                        pass
                # Also reload token if it was just generated
                if not self.token:
                    secret_file = backend_dir / "data" / ".hub_secret"
                    if secret_file.exists():
                        try:
                            self.token = secret_file.read_text().strip()
                            self.session.headers.update({
                                "X-Hub-Token": self.token,
                                "Authorization": f"Bearer {self.token}",
                            })
                        except Exception:
                            pass

                if self.is_hub_online():
                    logger.info(f"[AntigravityNotify] Hub backend active on {self.hub_url}")
                    return True
        except Exception as ex:
            logger.warning(f"Could not auto-start hub backend: {ex}")

        return False

    def _copy_screenshot(self, screenshot_path: Optional[str]) -> Optional[str]:
        if not screenshot_path:
            return None
        src = Path(screenshot_path)
        if not src.exists():
            return None
        filename = f"{int(time.time())}_{src.name}"
        dest = self.screenshots_dir / filename
        try:
            shutil.copy2(src, dest)
            # Include token query param so mobile Image components can view securely
            token_query = f"?token={self.token}" if self.token else ""
            return f"{self.hub_url}/api/screenshots/{filename}{token_query}"
        except Exception as e:
            logger.debug(f"Could not copy screenshot to hub: {e}")
            return None

    def send(
        self,
        title: str,
        message: str,
        workflow: str = "general",
        level: str = "info",        # info, success, warning, error, critical
        category: str = "general",  # job_applied, captcha, otp, milestone, error
        screenshot_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Sends an instant notification to the mobile app.
        Auto-starts the backend if it is not currently running.
        """
        self.ensure_hub_running()
        screenshot_url = self._copy_screenshot(screenshot_path)
        payload = {
            "workflow": workflow,
            "title": title,
            "message": message,
            "level": level,
            "category": category,
            "screenshot_url": screenshot_url,
            "metadata": metadata or {},
        }
        try:
            r = self.session.post(f"{self.hub_url}/api/notify", json=payload, timeout=2.5)
            return r.status_code == 200
        except Exception as e:
            logger.debug(f"[AntigravityNotify] Hub unreachable ({e}). Notification skipped.")
            return False

    def request_action(
        self,
        title: str,
        prompt: str,
        workflow: str = "general",
        message: str = "",
        action_type: str = "input",    # input (OTP/text), confirm (Approve/Reject), choice
        options: Optional[List[str]] = None,
        timeout_seconds: int = 120,
        screenshot_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        action_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Requests human intervention from your mobile phone!
        Blocks synchronously until you submit the OTP/action on your phone, or timeout occurs.
        Returns the user's response string (e.g., '581920' or 'APPROVE'), or None if timed out.
        """
        self.ensure_hub_running()
        screenshot_url = self._copy_screenshot(screenshot_path)
        actual_action_id = action_id or f"act_{int(time.time()*1000)}"

        payload = {
            "workflow": workflow,
            "title": title,
            "message": message or prompt,
            "level": "warning" if action_type == "input" else "info",
            "category": "otp" if "otp" in title.lower() else "action_required",
            "screenshot_url": screenshot_url,
            "action": {
                "action_id": actual_action_id,
                "action_type": action_type,
                "prompt": prompt,
                "options": options or (["Approve", "Reject"] if action_type == "confirm" else []),
                "timeout_seconds": timeout_seconds,
            },
            "metadata": metadata or {},
        }

        try:
            logger.info(f"Waiting for mobile action '{prompt}' (Timeout: {timeout_seconds}s)...")
            r = self.session.post(f"{self.hub_url}/api/request-action", json=payload, timeout=timeout_seconds + 5)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "resolved":
                    logger.info(f"Received mobile response: '{data.get('response')}'")
                    return data.get("response")
                else:
                    logger.warning(f"Action '{actual_action_id}' ended with status: {data.get('status')}")
            return None
        except Exception as e:
            logger.warning(f"Error requesting mobile action: {e}")
            return None

    def get_daily_prep(self) -> Dict[str, Any]:
        """Fetches today's active interview preparation questions from the local Hub."""
        self.ensure_hub_running()
        try:
            r = self.session.get(f"{self.hub_url}/api/qna/daily", timeout=2.0)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning(f"Error fetching daily prep: {e}")
        return {"items": [], "total_questions": 0}

    def trigger_prep_pipeline(self, slot_id: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
        """Triggers the autonomous multi-agent interview questions pipeline."""
        self.ensure_hub_running()
        try:
            r = self.session.post(
                f"{self.hub_url}/api/qna/trigger",
                json={"slot_id": slot_id, "force": force},
                timeout=15.0,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning(f"Error triggering prep pipeline: {e}")
        return {"status": "error"}


# Global singleton instance for easy import:
# from client_sdk.antigravity_notify import notify
notify = AntigravityNotifier()
