import unittest
from fastapi.testclient import TestClient

from app import app
from config.settings import get_or_create_hub_token


class TestApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.token = get_or_create_hub_token()
        self.auth_headers = {
            "X-Hub-Token": self.token,
            "Content-Type": "application/json",
        }

    def test_public_status_endpoint(self):
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("db_path", data)
        self.assertIn("active_slot", data)

    def test_auth_verify_unauthorized(self):
        # Missing token -> 401
        res = self.client.get("/api/auth/verify")
        self.assertEqual(res.status_code, 401)

        # Invalid token -> 401
        res_bad = self.client.get("/api/auth/verify", headers={"X-Hub-Token": "invalid_wrong_token"})
        self.assertEqual(res_bad.status_code, 401)

    def test_auth_verify_authorized(self):
        # Valid X-Hub-Token header -> 200
        res = self.client.get("/api/auth/verify", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "authenticated")

        # Valid Bearer header -> 200
        res_bearer = self.client.get("/api/auth/verify", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(res_bearer.status_code, 200)
        self.assertEqual(res_bearer.json().get("status"), "authenticated")

        # Valid Query parameter -> 200
        res_query = self.client.get(f"/api/auth/verify?token={self.token}")
        self.assertEqual(res_query.status_code, 200)
        self.assertEqual(res_query.json().get("status"), "authenticated")

    def test_screenshot_path_traversal_and_auth(self):
        # 1. No token -> 401
        res_no_auth = self.client.get("/screenshots/test.png")
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. Filename traversal attempt with .. -> 400
        res_traversal = self.client.get("/screenshots/..evil.png", headers=self.auth_headers)
        self.assertEqual(res_traversal.status_code, 400)

        # 3. Filename starting with . (hidden) -> 400
        res_hidden = self.client.get("/screenshots/.hidden_file", headers=self.auth_headers)
        self.assertEqual(res_hidden.status_code, 400)

        # 4. Nonexistent clean file with valid token -> 404
        res_valid = self.client.get("/screenshots/nonexistent_shot.png", headers=self.auth_headers)
        self.assertEqual(res_valid.status_code, 404)

    def test_qna_daily_endpoint(self):
        # Without auth -> 401
        res_unauth = self.client.get("/api/qna/daily")
        self.assertEqual(res_unauth.status_code, 401)

        # With auth -> 200
        res = self.client.get("/api/qna/daily", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("date", data)
        self.assertIn("items", data)
        self.assertIn("slot_progress", data)
        self.assertIn("total_questions", data)

    def test_qna_history_endpoint(self):
        # Without auth -> 401
        res_unauth = self.client.get("/api/qna/history")
        self.assertEqual(res_unauth.status_code, 401)

        # With auth -> 200
        res = self.client.get("/api/qna/history?page=1&page_size=5", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)
        self.assertIn("page", data)
        self.assertIn("total", data)


if __name__ == "__main__":
    unittest.main()
