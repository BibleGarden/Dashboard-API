import unittest
import os
from datetime import timedelta

from fastapi.testclient import TestClient
from main import app
import stats as stats_module
from database import create_connection


class TestStats(unittest.TestCase):
    """Tests for the /api/stats endpoints (summary groups/trends, recent filters)"""

    def setUp(self):
        self.client = TestClient(app)
        login_response = self.client.post("/api/auth/login", json={
            "username": os.getenv("ADMIN_USERNAME", "admin"),
            "password": os.environ["TEST_ADMIN_PASSWORD"],
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
            cursor.execute("SELECT CURDATE(), NOW()")
            self.today, self.now = cursor.fetchone()
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
        created_at = self.now - timedelta(days=days_ago)
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
        # Aggregated rows: current period (10 and 2 days ago) and previous period (40 days ago)
        self._insert_daily(self.today - timedelta(days=10), "/api/translations", 100, errors=5, avg_ms=40)
        self._insert_daily(self.today - timedelta(days=10), "/api/ai/question", 20, errors=2, avg_ms=900)
        self._insert_daily(self.today - timedelta(days=10), "_total_", 120, errors=7, avg_ms=183)
        self._insert_daily(self.today - timedelta(days=2), "/api/translations", 50, errors=0, avg_ms=60)
        self._insert_daily(self.today - timedelta(days=40), "/api/translations", 200, errors=10, avg_ms=30)
        self._insert_daily(self.today - timedelta(days=40), "_total_", 200, errors=10, avg_ms=30)
        # Raw rows: today (live) — scripture, ai and error traffic
        self._insert_raw("/api/translations", status=200, ms=30, ip="10.0.0.1")
        self._insert_raw("/api/translations", status=404, ms=40, ip="10.0.0.2")
        self._insert_raw("/api/ai/question", method="POST", status=200, ms=800, ip="10.0.0.3")
        # Slow endpoint: enough rows to pass the SLOW_ENDPOINTS_MIN_REQUESTS threshold
        for _ in range(12):
            self._insert_raw("/api/slow", status=200, ms=2000, days_ago=1)
        # Raw row inside the previous seven-calendar-day window D-13..D-7.
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
        self.assertEqual(data["groups"]["scripture"]["avg_response_time_ms"], 47)
        self.assertEqual(data["groups"]["ai"]["avg_response_time_ms"], 895)

    def test_summary_uses_exact_calendar_boundaries_everywhere(self):
        response = self.client.get("/api/stats/summary?days=10", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # D-10 is the last day of the previous period, not the first day of
        # the 10-day current period D-9..D.
        self.assertEqual(data["totals"]["total_requests"], 53)
        self.assertEqual(data["previous_totals"]["total_requests"], 120)
        self.assertEqual(data["groups"]["scripture"]["requests"], 52)
        self.assertEqual(data["groups"]["ai"]["requests"], 1)

        boundary = str(self.today - timedelta(days=10))
        self.assertNotIn(boundary, {row["date"] for row in data["daily"]})
        self.assertNotIn(boundary, {row["date"] for row in data["daily_groups"]})
        endpoints = {row["endpoint"]: row for row in data["top_endpoints"]}
        self.assertEqual(endpoints["/api/translations"]["requests"], 52)
        self.assertEqual(endpoints["/api/ai/question"]["requests"], 1)

    def test_summary_uses_request_weighted_response_times(self):
        response = self.client.get("/api/stats/summary?days=30", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Current total includes the three raw requests from today. Averages
        # are weighted by request count, not by the number of aggregate rows.
        self.assertEqual(data["totals"]["total_requests"], 173)
        self.assertEqual(data["totals"]["avg_response_time_ms"], 150)
        self.assertEqual(data["groups"]["scripture"]["avg_response_time_ms"], 47)
        endpoints = {row["endpoint"]: row for row in data["top_endpoints"]}
        self.assertEqual(endpoints["/api/translations"]["avg_response_time_ms"], 47)

    def test_summary_previous_totals(self):
        response = self.client.get("/api/stats/summary?days=7", headers=self.headers)
        data = response.json()

        # Previous window D-13..D-7: the 10-days-ago daily rows
        # (scripture 100/5 errors + ai 20/2 errors) plus the raw row with ip 10.9.9.9
        self.assertEqual(data["previous_totals"]["total_requests"], 120)
        self.assertEqual(data["previous_totals"]["total_errors"], 7)
        self.assertEqual(data["previous_totals"]["avg_response_time_ms"], 183)
        self.assertEqual(data["previous_totals"]["unique_ips"], 1)

    def test_summary_previous_unique_ips_require_full_raw_interval(self):
        available = self.client.get(
            "/api/stats/summary?days=7", headers=self.headers
        ).json()
        unavailable = self.client.get(
            "/api/stats/summary?days=8", headers=self.headers
        ).json()

        self.assertEqual(available["previous_totals"]["unique_ips"], 1)
        self.assertIsNone(unavailable["previous_totals"]["unique_ips"])

    def test_summary_daily_groups(self):
        response = self.client.get("/api/stats/summary?days=30", headers=self.headers)
        data = response.json()

        rows = {(r["date"], r["grp"]): r["requests"] for r in data["daily_groups"]}
        scripture_today = rows.get((str(self.today), "scripture"))
        ai_today = rows.get((str(self.today), "ai"))
        self.assertEqual(scripture_today, 2)
        self.assertEqual(ai_today, 1)

    def test_summary_filters_top_endpoints_before_limit_only(self):
        for index in range(21):
            self._insert_daily(
                self.today - timedelta(days=1),
                f"/api/high-traffic-{index}",
                100 + index,
            )
        self._insert_daily(
            self.today - timedelta(days=1), "/health/internal", 1, avg_ms=777
        )
        self._insert_daily(
            self.today - timedelta(days=1), "/health/percent%literal", 2
        )
        self._insert_daily(
            self.today - timedelta(days=1), "/health/percentXliteral", 3
        )

        unfiltered = self.client.get(
            "/api/stats/summary?days=30", headers=self.headers
        ).json()
        filtered_response = self.client.get(
            "/api/stats/summary?days=30&top_group=other&top_endpoint=internal",
            headers=self.headers,
        )
        self.assertEqual(filtered_response.status_code, 200)
        filtered = filtered_response.json()

        self.assertNotIn(
            "/health/internal",
            {row["endpoint"] for row in unfiltered["top_endpoints"]},
        )
        self.assertEqual(
            [row["endpoint"] for row in filtered["top_endpoints"]],
            ["/health/internal"],
        )
        self.assertEqual(filtered["totals"], unfiltered["totals"])
        self.assertEqual(filtered["groups"], unfiltered["groups"])

        literal_percent = self.client.get(
            "/api/stats/summary",
            params={"days": 30, "top_group": "other", "top_endpoint": "percent%"},
            headers=self.headers,
        ).json()
        self.assertEqual(
            [row["endpoint"] for row in literal_percent["top_endpoints"]],
            ["/health/percent%literal"],
        )

    def test_summary_rejects_invalid_top_group(self):
        response = self.client.get(
            "/api/stats/summary?top_group=invalid", headers=self.headers
        )
        self.assertEqual(response.status_code, 422)

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

    def test_recent_substring_filters_treat_like_metacharacters_as_literals(self):
        self._insert_raw("/api/literal_value", ip="client_tag")
        self._insert_raw("/api/literalXvalue", ip="clientXtag")

        response = self.client.get(
            "/api/stats/recent",
            params={"limit": 100, "endpoint": "literal_", "client_ip": "client_"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["endpoint"] for row in response.json()["items"]],
            ["/api/literal_value"],
        )

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
        for status in ("abc", "2x0"):
            with self.subTest(status=status):
                response = self.client.get(
                    f"/api/stats/recent?limit=10&status={status}",
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    unittest.main()
