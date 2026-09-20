import unittest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from main import app
import stats as stats_module
from database import create_connection


class TestStats(unittest.TestCase):
    """Tests for the /api/stats endpoints (summary groups/trends, recent filters)"""

    def setUp(self):
        self.client = TestClient(app)
        login_response = self.client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        self.assertEqual(login_response.status_code, 200)
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Redirect stats queries from cep_public to the test database
        self._public_db = stats_module.PUBLIC_DB_NAME
        stats_module.PUBLIC_DB_NAME = "cep_test"

        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cep_test.api_requests (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    endpoint VARCHAR(255) NOT NULL,
                    method VARCHAR(10) NOT NULL,
                    status_code SMALLINT UNSIGNED NOT NULL,
                    response_time_ms INT UNSIGNED NOT NULL,
                    client_ip VARCHAR(45) NOT NULL,
                    user_agent VARCHAR(512) DEFAULT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created_at (created_at),
                    INDEX idx_endpoint (endpoint)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cep_test.api_request_daily_stats (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    date DATE NOT NULL,
                    endpoint VARCHAR(255) NOT NULL,
                    request_count INT UNSIGNED NOT NULL DEFAULT 0,
                    unique_ips INT UNSIGNED NOT NULL DEFAULT 0,
                    avg_response_time_ms INT UNSIGNED NOT NULL DEFAULT 0,
                    error_count INT UNSIGNED NOT NULL DEFAULT 0,
                    UNIQUE KEY uk_date_endpoint (date, endpoint)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("DELETE FROM cep_test.api_requests")
            cursor.execute("DELETE FROM cep_test.api_request_daily_stats")
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self._seed()

    def tearDown(self):
        stats_module.PUBLIC_DB_NAME = self._public_db
        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM cep_test.api_requests")
            cursor.execute("DELETE FROM cep_test.api_request_daily_stats")
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    # ------------------------------------------------------------- fixtures ----

    def _insert_raw(self, endpoint, method="GET", status=200, ms=50,
                    ip="10.0.0.1", days_ago=0):
        created_at = datetime.now() - timedelta(days=days_ago)
        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO cep_test.api_requests
                    (endpoint, method, status_code, response_time_ms, client_ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (endpoint, method, status, ms, ip, created_at.strftime("%Y-%m-%d %H:%M:%S")))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _insert_daily(self, date, endpoint, requests, errors=0, avg_ms=50, unique_ips=1):
        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO cep_test.api_request_daily_stats
                    (date, endpoint, request_count, unique_ips, avg_response_time_ms, error_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (date, endpoint, requests, unique_ips, avg_ms, errors))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _seed(self):
        today = datetime.now().date()
        # Aggregated rows: current period (10 and 2 days ago) and previous period (40 days ago)
        self._insert_daily(today - timedelta(days=10), "/api/translations", 100, errors=5, avg_ms=40)
        self._insert_daily(today - timedelta(days=10), "/api/ai/question", 20, errors=2, avg_ms=900)
        self._insert_daily(today - timedelta(days=2), "/api/translations", 50, errors=0, avg_ms=60)
        self._insert_daily(today - timedelta(days=40), "/api/translations", 200, errors=10, avg_ms=30)
        self._insert_daily(today - timedelta(days=40), "_total_", 200, errors=10, avg_ms=30)
        # Raw rows: today (live) — scripture, ai and error traffic
        self._insert_raw("/api/translations", status=200, ms=30, ip="10.0.0.1")
        self._insert_raw("/api/translations", status=404, ms=40, ip="10.0.0.2")
        self._insert_raw("/api/ai/question", method="POST", status=200, ms=800, ip="10.0.0.3")
        # Slow endpoint: enough rows to pass the SLOW_ENDPOINTS_MIN_REQUESTS threshold
        for _ in range(12):
            self._insert_raw("/api/slow", status=200, ms=2000, days_ago=1)
        # Raw row inside the [7, 14) days previous window
        self._insert_raw("/api/translations", status=200, ms=30, ip="10.9.9.9", days_ago=10)

    # ---------------------------------------------------------------- tests ----

    def test_summary_response_structure(self):
        response = self.client.get("/api/stats/summary?days=30", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        for key in ("period_days", "totals", "previous_totals", "today",
                    "groups", "daily", "daily_groups", "top_endpoints",
                    "slow_endpoints"):
            self.assertIn(key, data)

        for group in ("scripture", "ai", "other"):
            self.assertIn(group, data["groups"])
            for field in ("requests", "errors", "avg_response_time_ms"):
                self.assertIn(field, data["groups"][group])

    def test_summary_groups_classification(self):
        response = self.client.get("/api/stats/summary?days=30", headers=self.headers)
        data = response.json()

        # scripture: 100 + 50 aggregated + 2 raw today; ai: 20 + 1 raw today
        self.assertEqual(data["groups"]["scripture"]["requests"], 152)
        self.assertEqual(data["groups"]["ai"]["requests"], 21)
        self.assertEqual(data["groups"]["scripture"]["errors"], 5 + 1)
        self.assertEqual(data["groups"]["ai"]["errors"], 2)

    def test_summary_previous_totals(self):
        response = self.client.get("/api/stats/summary?days=7", headers=self.headers)
        data = response.json()

        # Previous window [14, 7) days: the 10-days-ago daily rows
        # (scripture 100/5 errors + ai 20/2 errors) plus the raw row with ip 10.9.9.9
        self.assertEqual(data["previous_totals"]["total_requests"], 120)
        self.assertEqual(data["previous_totals"]["total_errors"], 7)
        self.assertEqual(data["previous_totals"]["unique_ips"], 1)

    def test_summary_previous_unique_ips_unavailable_for_long_periods(self):
        response = self.client.get("/api/stats/summary?days=90", headers=self.headers)
        data = response.json()
        self.assertIsNone(data["previous_totals"]["unique_ips"])

    def test_summary_daily_groups(self):
        response = self.client.get("/api/stats/summary?days=30", headers=self.headers)
        data = response.json()

        rows = {(r["date"], r["grp"]): r["requests"] for r in data["daily_groups"]}
        scripture_today = rows.get((str(datetime.now().date()), "scripture"))
        ai_today = rows.get((str(datetime.now().date()), "ai"))
        self.assertEqual(scripture_today, 2)
        self.assertEqual(ai_today, 1)

    def test_summary_slow_endpoints(self):
        response = self.client.get("/api/stats/summary?days=30", headers=self.headers)
        data = response.json()

        slow = {r["endpoint"]: r for r in data["slow_endpoints"]}
        self.assertIn("/api/slow", slow)
        self.assertEqual(slow["/api/slow"]["avg_response_time_ms"], 2000)
        self.assertEqual(slow["/api/slow"]["max_response_time_ms"], 2000)
        self.assertEqual(slow["/api/slow"]["requests"], 12)

    def test_recent_without_filters(self):
        response = self.client.get("/api/stats/recent?limit=100", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 16)

    def test_recent_filter_by_endpoint(self):
        response = self.client.get(
            "/api/stats/recent?limit=100&endpoint=/api/ai/", headers=self.headers)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["endpoint"], "/api/ai/question")

    def test_recent_filter_by_status_class(self):
        response = self.client.get(
            "/api/stats/recent?limit=100&status=4xx", headers=self.headers)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["status_code"], 404)

    def test_recent_filter_by_method_and_ip(self):
        response = self.client.get(
            "/api/stats/recent?limit=100&method=post&client_ip=10.0.0.3",
            headers=self.headers)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["method"], "POST")

    def test_recent_invalid_status_rejected(self):
        response = self.client.get(
            "/api/stats/recent?limit=10&status=abc", headers=self.headers)
        self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    unittest.main()
