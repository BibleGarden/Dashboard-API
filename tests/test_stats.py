import unittest
import os
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from main import app
import stats as stats_module
from config import DB_TIME_ZONE
from database import create_connection


class TestStats(unittest.TestCase):
    """Tests for the /api/stats endpoints (summary periods, errors, recent filters)"""

    @classmethod
    def setUpClass(cls):
        # Stats rows live in a private schema; other agents may use cep_test.
        cls.stats_db = f"cep_stats_ip_{uuid.uuid4().hex[:12]}"
        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(f"CREATE DATABASE {cls.stats_db} CHARACTER SET utf8mb4")
        finally:
            cursor.close()
            connection.close()

    @classmethod
    def tearDownClass(cls):
        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(f"DROP DATABASE {cls.stats_db}")
        finally:
            cursor.close()
            connection.close()

    def setUp(self):
        self.client = TestClient(app)
        login_response = self.client.post("/api/auth/login", json={
            "username": os.getenv("ADMIN_USERNAME", "admin"),
            "password": os.environ["TEST_ADMIN_PASSWORD"],
        })
        self.assertEqual(login_response.status_code, 200)
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Redirect stats queries from cep_public to this class's private schema.
        self._public_db = stats_module.PUBLIC_DB_NAME
        stats_module.PUBLIC_DB_NAME = self.stats_db

        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.stats_db}.api_requests (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    endpoint VARCHAR(255) NOT NULL,
                    application VARCHAR(32) NOT NULL,
                    method VARCHAR(10) NOT NULL,
                    status_code SMALLINT UNSIGNED NOT NULL,
                    response_time_ms INT UNSIGNED NOT NULL,
                    client_ip VARCHAR(45) NOT NULL,
                    user_agent VARCHAR(512) DEFAULT NULL,
                    degraded_reason VARCHAR(32) NULL DEFAULT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created_at (created_at),
                    INDEX idx_endpoint (endpoint)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.stats_db}.api_request_daily_stats (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    date DATE NOT NULL,
                    endpoint VARCHAR(255) NOT NULL,
                    application VARCHAR(32) NOT NULL,
                    request_count INT UNSIGNED NOT NULL DEFAULT 0,
                    unique_ips INT UNSIGNED NOT NULL DEFAULT 0,
                    avg_response_time_ms INT UNSIGNED NOT NULL DEFAULT 0,
                    error_count INT UNSIGNED NOT NULL DEFAULT 0,
                    server_error_count INT UNSIGNED NULL DEFAULT NULL,
                    degraded_count INT UNSIGNED NULL DEFAULT NULL,
                    UNIQUE KEY uk_date_endpoint_application (date, endpoint, application)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute(f"DELETE FROM {self.stats_db}.api_requests")
            cursor.execute(f"DELETE FROM {self.stats_db}.api_request_daily_stats")
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
            cursor.execute(f"DELETE FROM {self.stats_db}.api_requests")
            cursor.execute(f"DELETE FROM {self.stats_db}.api_request_daily_stats")
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    # ------------------------------------------------------------- fixtures ----

    def _execute(self, sql, params=()):
        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _insert_raw(self, endpoint, method="GET", status=200, ms=50,
                    ip="a" * 40, days_ago=0, hours_ago=0,
                    application="bible-garden", degraded_reason=None):
        created_at = self.now - timedelta(days=days_ago, hours=hours_ago)
        self._execute(f"""
            INSERT INTO {self.stats_db}.api_requests
                (endpoint, application, method, status_code, response_time_ms,
                 client_ip, degraded_reason, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (endpoint, application, method, status, ms, ip, degraded_reason,
              created_at.strftime("%Y-%m-%d %H:%M:%S")))
        return created_at

    def _insert_daily(self, date, endpoint, requests, errors=0, avg_ms=50,
                      unique_ips=1, application="bible-garden",
                      server_errors=None, degraded=None):
        """Insert an aggregate row; a bible-garden endpoint row also gets its
        overall application='all' twin, like the aggregator writes."""
        applications = [application]
        if application == "bible-garden" and endpoint != "_total_":
            applications.append("all")
        for row_application in applications:
            self._execute(f"""
                INSERT INTO {self.stats_db}.api_request_daily_stats
                    (date, endpoint, application, request_count, unique_ips,
                     avg_response_time_ms, error_count, server_error_count, degraded_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (date, endpoint, row_application, requests, unique_ips, avg_ms,
                  errors, server_errors, degraded))

    def _day(self, days_ago):
        return self.today - timedelta(days=days_ago)

    def _utc(self, value):
        return value.replace(tzinfo=ZoneInfo(DB_TIME_ZONE)).astimezone(
            timezone.utc).isoformat().replace("+00:00", "Z")

    def _seed(self):
        # D-40: aggregated before the failure counters existed (NULL).
        self._insert_daily(self._day(40), "/api/translations", 200, errors=10, avg_ms=30)
        self._insert_daily(self._day(40), "_total_", 200, errors=10, avg_ms=30,
                           application="all")
        # D-20 is the first day with counters.
        self._insert_daily(self._day(20), "/api/translations", 10, avg_ms=20,
                           server_errors=0, degraded=0)
        self._insert_daily(self._day(20), "_total_", 10, avg_ms=20, application="all",
                           server_errors=0, degraded=0)
        self._insert_daily(self._day(10), "/api/translations", 100, errors=5, avg_ms=40,
                           server_errors=2, degraded=0)
        self._insert_daily(self._day(10), "/api/ai/question", 20, errors=2, avg_ms=900,
                           server_errors=1, degraded=3)
        self._insert_daily(self._day(10), "_total_", 120, errors=7, avg_ms=183,
                           unique_ips=9, application="all", server_errors=3, degraded=3)
        self._insert_daily(self._day(2), "/api/translations", 50, avg_ms=60,
                           server_errors=0, degraded=0)
        self._insert_daily(self._day(2), "_total_", 50, avg_ms=60, unique_ips=4,
                           application="all", server_errors=0, degraded=0)
        # Raw rows: today (live) — scripture, a client error and a degraded AI answer.
        self._insert_raw("/api/translations", status=200, ms=30, ip="a" * 40)
        self._insert_raw("/api/translations", status=404, ms=40, ip="b" * 40)
        self._insert_raw("/api/ai/question", method="POST", status=200, ms=800,
                         ip="c" * 40, degraded_reason="format_retry_failed")
        # The earliest raw row: raw rows cover the last ten days.
        self.raw_from = self._insert_raw("/api/translations", ip="f" * 40, days_ago=10)

    def _summary(self, **params):
        response = self.client.get("/api/stats/summary", params=params, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _dates(self, first_days_ago, last_days_ago=0):
        return {"date_from": str(self._day(first_days_ago)),
                "date_to": str(self._day(last_days_ago))}

    # ----------------------------------------------------------- hours mode ----

    def test_hours_mode_is_the_default_and_reads_raw_rows(self):
        self._insert_raw("/api/translations", status=500, ip="e" * 40, hours_ago=30)
        data = self._summary()

        self.assertEqual(data["period"], {"mode": "hours", "hours": 24, "date_from": None,
                                          "date_to": None, "bucket": "hour"})
        self.assertEqual(data["totals"], {
            "requests": 3, "unique_clients": 3, "server_errors": 0, "client_errors": 1,
            "degraded": 1, "avg_response_time_ms": 290,
        })
        # Previous window [now-48h, now-24h) holds the 30-hours-ago 500.
        self.assertEqual(data["previous"], {
            "requests": 1, "unique_clients": 1, "server_errors": 1, "client_errors": 0,
            "degraded": 0, "avg_response_time_ms": 50,
        })
        self.assertEqual(data["coverage"], {"raw_since": None, "server_errors_since": None,
                                            "degraded_since": None})

    def test_hours_mode_series_is_hourly_and_zero_filled(self):
        self._insert_raw("/api/ai/scripture", method="POST", status=502, ip="d" * 40,
                         hours_ago=3)
        series = self._summary(hours=6)["series"]

        self.assertEqual(len(series), 7)
        starts = [datetime.fromisoformat(row["bucket_start"].replace("Z", "+00:00"))
                  for row in series]
        self.assertTrue(all(b - a == timedelta(hours=1) for a, b in zip(starts, starts[1:])))
        self.assertTrue(all(value.minute == 0 and value.second == 0 for value in starts))
        self.assertEqual(sum(row["requests"] for row in series), 4)
        self.assertEqual(series[-1]["requests"], 3)
        self.assertEqual(series[-1]["scripture_requests"], 2)
        self.assertEqual(series[-1]["ai_requests"], 1)
        self.assertEqual(series[-1]["degraded"], 1)
        self.assertEqual(series[-4]["server_errors"], 1)
        self.assertEqual(series[-4]["ai_requests"], 1)
        self.assertEqual(series[0]["requests"], 0)

    def test_hours_mode_previous_is_unknown_beyond_raw_rows(self):
        data = self._summary(hours=336)

        self.assertEqual(set(data["previous"].values()), {None})
        self.assertEqual(data["coverage"]["raw_since"], self._utc(self.raw_from))
        self.assertEqual(data["totals"]["requests"], 4)

    # ------------------------------------------------------------ date mode ----

    def test_date_mode_combines_daily_aggregates_and_today(self):
        data = self._summary(**self._dates(9))

        self.assertEqual(data["period"], {"mode": "dates", "hours": None,
                                          "date_from": str(self._day(9)),
                                          "date_to": str(self.today), "bucket": "day"})
        # D-2 aggregate (50 requests at 60 ms) plus three raw rows today
        # (870 ms in total): weighted average 3870 / 53.
        self.assertEqual(data["totals"], {
            "requests": 53, "unique_clients": 3, "server_errors": 0, "client_errors": 1,
            "degraded": 1, "avg_response_time_ms": 73,
        })
        self.assertEqual(data["coverage"], {"raw_since": None, "server_errors_since": None,
                                            "degraded_since": None})

    def test_date_mode_previous_period_has_equal_length(self):
        # D-19..D-10 precedes D-9..D; its raw rows are gone, so unique clients are unknown.
        data = self._summary(**self._dates(9))
        self.assertEqual(data["previous"], {
            "requests": 120, "unique_clients": None, "server_errors": 3, "client_errors": 4,
            "degraded": 3, "avg_response_time_ms": 183,
        })

        # D-9..D-5 precedes D-4..D and lies inside the raw rows.
        self._insert_raw("/api/translations", ip="g" * 40, days_ago=6)
        previous = self._summary(**self._dates(4))["previous"]
        self.assertEqual(previous["unique_clients"], 1)
        self.assertEqual(previous["requests"], 0)

    def test_date_mode_excluding_today_ignores_raw_rows(self):
        data = self._summary(**self._dates(9, 1))
        self.assertEqual(data["totals"]["requests"], 50)
        self.assertEqual(data["totals"]["degraded"], 0)
        self.assertEqual(len(data["series"]), 9)

    def test_counters_are_null_before_the_first_counted_day(self):
        uncounted = self._summary(**self._dates(45, 35))
        self.assertEqual(uncounted["totals"]["requests"], 200)
        # The range ends before the earliest raw row: no unique clients at all.
        self.assertIsNone(uncounted["totals"]["unique_clients"])
        self.assertIsNone(uncounted["previous"]["unique_clients"])
        for key in ("server_errors", "client_errors", "degraded"):
            self.assertIsNone(uncounted["totals"][key])
            self.assertIsNone(uncounted["previous"][key])
        self.assertEqual(uncounted["coverage"]["server_errors_since"], str(self._day(20)))
        self.assertEqual(uncounted["coverage"]["degraded_since"], str(self._day(20)))
        self.assertEqual({row["server_errors"] for row in uncounted["series"]}, {None})
        apps = {row["application"]: row for row in uncounted["applications"]}
        self.assertIsNone(apps["bible-garden"]["server_errors"])
        self.assertEqual(apps["bible-garden"]["requests"], 200)

        partial = self._summary(**self._dates(30))
        self.assertEqual(partial["totals"]["unique_clients"], 4)
        self.assertEqual(partial["totals"]["server_errors"], 3)
        self.assertEqual(partial["totals"]["client_errors"], 5)
        self.assertEqual(partial["coverage"]["server_errors_since"], str(self._day(20)))
        self.assertEqual(partial["coverage"]["raw_since"], self._utc(self.raw_from))
        self.assertIsNone(partial["previous"]["server_errors"])
        by_day = {row["bucket_start"]: row for row in partial["series"]}
        self.assertIsNone(by_day[str(self._day(21))]["server_errors"])
        self.assertEqual(by_day[str(self._day(19))]["server_errors"], 0)
        self.assertEqual(by_day[str(self._day(10))]["server_errors"], 3)

    def test_degraded_coverage_is_independent_of_server_errors(self):
        # Recomputed legacy days get server_error_count but keep degraded_count NULL.
        self._execute(f"""
            UPDATE {self.stats_db}.api_request_daily_stats
            SET degraded_count = NULL WHERE date < %s
        """, (self._day(2),))
        data = self._summary(**self._dates(30))
        self.assertEqual(data["coverage"]["server_errors_since"], str(self._day(20)))
        self.assertEqual(data["coverage"]["degraded_since"], str(self._day(2)))
        self.assertEqual(data["totals"]["server_errors"], 3)
        self.assertEqual(data["totals"]["degraded"], 1)
        by_day = {row["bucket_start"]: row for row in data["series"]}
        self.assertEqual(by_day[str(self._day(10))]["server_errors"], 3)
        self.assertIsNone(by_day[str(self._day(10))]["degraded"])
        self.assertEqual(by_day[str(self._day(2))]["degraded"], 0)

    def test_only_today_is_counted_when_no_day_has_counters(self):
        self._execute(f"""
            UPDATE {self.stats_db}.api_request_daily_stats
            SET server_error_count = NULL, degraded_count = NULL
        """)
        data = self._summary(**self._dates(2))
        self.assertEqual(data["coverage"]["server_errors_since"], str(self.today))
        self.assertEqual(data["totals"]["degraded"], 1)
        self.assertEqual([row["degraded"] for row in data["series"]], [None, None, 1])

    def test_date_mode_series_is_daily_and_zero_filled(self):
        series = self._summary(**self._dates(9))["series"]

        self.assertEqual([row["bucket_start"] for row in series],
                         [str(self._day(days_ago)) for days_ago in range(9, -1, -1)])
        by_day = {row["bucket_start"]: row for row in series}
        self.assertEqual(by_day[str(self._day(2))]["requests"], 50)
        self.assertEqual(by_day[str(self._day(2))]["unique_clients"], 4)
        self.assertEqual(by_day[str(self._day(2))]["scripture_requests"], 50)
        self.assertEqual(by_day[str(self._day(5))], {
            "bucket_start": str(self._day(5)), "requests": 0, "unique_clients": 0,
            "server_errors": 0, "degraded": 0, "avg_response_time_ms": 0,
            "scripture_requests": 0, "ai_requests": 0,
        })
        today = by_day[str(self.today)]
        self.assertEqual((today["requests"], today["scripture_requests"],
                          today["ai_requests"], today["degraded"]), (3, 2, 1, 1))

    def test_daily_overall_total_does_not_sum_application_unique_clients(self):
        day = self._day(1)
        self._insert_daily(day, "/api/test", 1, application="lampada")
        self._insert_daily(day, "_total_", 1, application="lampada")
        self._insert_daily(day, "_total_", 1, application="bible-garden")
        self._insert_daily(day, "_total_", 2, unique_ips=1, application="all",
                           server_errors=0, degraded=0)
        series = self._summary(**self._dates(6))["series"]
        self.assertEqual(
            [(row["requests"], row["unique_clients"]) for row in series
             if row["bucket_start"] == str(day)],
            [(2, 1)],
        )

    def test_legacy_unknown_daily_total_remains_visible(self):
        day = self._day(30)
        self._insert_daily(day, "/api/legacy", 3, application="unknown")
        self._insert_daily(day, "_total_", 3, application="unknown")
        series = self._summary(**self._dates(30, 30))["series"]
        self.assertEqual([row["requests"] for row in series], [3])

    def test_recomputed_legacy_day_is_counted_once(self):
        # A pre-split day keeps its legacy 'unknown' rows (NULL counters) and
        # gains overall 'all' rows when the aggregator recomputes it.
        day = self._day(5)
        for application, server_errors in (("unknown", None), ("all", 1)):
            self._insert_daily(day, "/api/translations", 7, errors=2, avg_ms=10,
                               application=application, server_errors=server_errors,
                               degraded=server_errors)
            self._insert_daily(day, "_total_", 7, errors=2, avg_ms=10, unique_ips=2,
                               application=application, server_errors=server_errors,
                               degraded=server_errors)
        data = self._summary(**self._dates(6, 4))

        self.assertEqual(data["totals"]["requests"], 7)
        self.assertEqual(data["totals"]["server_errors"], 1)
        self.assertEqual(data["totals"]["client_errors"], 1)
        self.assertEqual([(row["requests"], row["unique_clients"], row["server_errors"])
                          for row in data["series"]], [(0, 0, 0), (7, 2, 1), (0, 0, 0)])
        apps = {row["application"]: row["requests"] for row in data["applications"]}
        self.assertEqual(apps, {"bible-garden": 0, "lampada": 0, "ops": 0, "unknown": 7})

    def test_application_breakdown_includes_legacy_unknown_and_live_lampada(self):
        self._insert_daily(self._day(1), "/api/legacy", 4, application="unknown")
        self._insert_raw("/api/ai/question", method="POST", status=503, ip="d" * 40,
                         application="lampada")
        apps = self._summary(**self._dates(29))["applications"]

        self.assertEqual([row["application"] for row in apps],
                         ["bible-garden", "lampada", "ops", "unknown"])
        apps = {row["application"]: row for row in apps}
        self.assertEqual(apps["unknown"]["requests"], 4)
        self.assertEqual(apps["lampada"], {"application": "lampada", "requests": 1,
                                           "server_errors": 1, "degraded": 0,
                                           "avg_response_time_ms": 50})
        self.assertEqual(apps["ops"]["requests"], 0)
        self.assertEqual(apps["bible-garden"]["requests"], 183)
        self.assertEqual(apps["bible-garden"]["server_errors"], 3)
        self.assertEqual(apps["bible-garden"]["degraded"], 4)

        hourly = {row["application"]: row for row in self._summary()["applications"]}
        self.assertEqual(hourly["bible-garden"]["requests"], 3)
        self.assertEqual(hourly["lampada"]["server_errors"], 1)

    # ----------------------------------------------------------- validation ----

    def test_period_parameters_are_validated(self):
        tomorrow = str(self.today + timedelta(days=1))
        cases = {
            "mixed": {"hours": 24, **self._dates(1)},
            "hours and one date": {"hours": 24, "date_from": str(self.today)},
            "only date_from": {"date_from": str(self.today)},
            "only date_to": {"date_to": str(self.today)},
            "reversed": {"date_from": str(self.today), "date_to": str(self._day(1))},
            "too long": self._dates(366),
            "future": {"date_from": str(self.today), "date_to": tomorrow},
            "zero hours": {"hours": 0},
            "too many hours": {"hours": 337},
            "bad date": {"date_from": "2026-13-01", "date_to": str(self.today)},
        }
        for path in ("/api/stats/summary", "/api/stats/errors"):
            for name, params in cases.items():
                with self.subTest(path=path, case=name):
                    response = self.client.get(path, params=params, headers=self.headers)
                    self.assertEqual(response.status_code, 422, response.text)

        self.assertEqual(len(self._summary(**self._dates(365))["series"]), 366)
        self.assertEqual(self._summary(hours=336)["period"]["hours"], 336)

    # ---------------------------------------------------------------- errors ----

    def test_errors_group_and_sort_failures_and_degradations(self):
        for _ in range(2):
            self._insert_raw("/api/ai/scripture", method="POST", status=502, ip="d" * 40)
            self._insert_raw("/api/translations", status=404, ip="d" * 40)
            self._insert_raw("/api/ai/scripture", method="POST", ip="d" * 40,
                             degraded_reason="rerank_failed")
        last_500 = self._insert_raw("/api/ai/question", method="POST", status=500,
                                    ip="d" * 40, hours_ago=1)
        # Outside the default 24 hours.
        self._insert_raw("/api/ai/question", method="POST", status=500, ip="d" * 40,
                         hours_ago=30)
        self._insert_raw("/api/ai/scripture", ip="d" * 40, hours_ago=30,
                         degraded_reason="deadline")

        response = self.client.get("/api/stats/errors", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()

        self.assertEqual(data["period"]["mode"], "hours")
        self.assertEqual(data["raw_available_from"], self._utc(self.raw_from))
        self.assertFalse(data["partial"])
        self.assertEqual(
            [(row["status_code"], row["method"], row["endpoint"], row["count"])
             for row in data["errors"]],
            [(502, "POST", "/api/ai/scripture", 2), (500, "POST", "/api/ai/question", 1),
             (404, "GET", "/api/translations", 3)],
        )
        self.assertEqual(data["errors"][1]["last_seen"], self._utc(last_500))
        self.assertEqual(
            [(row["reason"], row["endpoint"], row["count"]) for row in data["degradations"]],
            [("rerank_failed", "/api/ai/scripture", 2),
             ("format_retry_failed", "/api/ai/question", 1)],
        )
        self.assertTrue(data["degradations"][0]["last_seen"].endswith("Z"))

    def test_errors_are_partial_when_the_range_precedes_raw_rows(self):
        response = self.client.get("/api/stats/errors", params=self._dates(20),
                                   headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["partial"])
        self.assertEqual(data["period"]["bucket"], "day")
        self.assertEqual([row["status_code"] for row in data["errors"]], [404])

        inside = self.client.get("/api/stats/errors", params=self._dates(5),
                                 headers=self.headers).json()
        self.assertFalse(inside["partial"])

    # ---------------------------------------------------------------- recent ----

    def test_recent_without_filters(self):
        response = self.client.get("/api/stats/recent?limit=100", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 4)
        self.assertEqual(data["items"][0]["application"], "bible-garden")
        reasons = {row["endpoint"]: row["degraded_reason"] for row in data["items"]}
        self.assertEqual(reasons["/api/ai/question"], "format_retry_failed")
        self.assertIsNone(reasons["/api/translations"])

    def test_recent_application_filter(self):
        self._insert_raw("/api/ai/question", application="lampada", ip="d" * 40)
        response = self.client.get(
            "/api/stats/recent", params={"application": "lampada"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["items"][0]["application"], "lampada")
        invalid = self.client.get(
            "/api/stats/recent", params={"application": "all"},
            headers=self.headers,
        )
        self.assertEqual(invalid.status_code, 422)

    def test_recent_filter_by_endpoint(self):
        response = self.client.get(
            "/api/stats/recent?limit=100&endpoint=/api/ai/", headers=self.headers)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["endpoint"], "/api/ai/question")

    def test_recent_endpoint_substring_treats_like_metacharacters_as_literals(self):
        self._insert_raw("/api/literal_value", ip="e" * 40)
        self._insert_raw("/api/literalXvalue", ip="f" * 40)

        response = self.client.get(
            "/api/stats/recent",
            params={"limit": 100, "endpoint": "literal_"},
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

    def test_recent_filter_by_method_and_pseudonym_prefix_or_full_value(self):
        response = self.client.get(
            "/api/stats/recent?limit=100&method=post&client_pseudonym=CCCCCCCC",
            headers=self.headers)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["method"], "POST")
        self.assertEqual(data["items"][0]["client_pseudonym"], "c" * 40)

        full = self.client.get(
            "/api/stats/recent", params={"client_pseudonym": "c" * 40},
            headers=self.headers,
        )
        self.assertEqual(full.json()["count"], 1)
        suffix = self.client.get(
            "/api/stats/recent", params={"client_pseudonym": "c" * 39 + "a"},
            headers=self.headers,
        )
        self.assertEqual(suffix.json()["count"], 0)

    def test_recent_rejects_non_hex_pseudonym_filter(self):
        for value in ("10.0.0.3", "abc%", "abc_"):
            with self.subTest(value=value):
                response = self.client.get(
                    "/api/stats/recent", params={"client_pseudonym": value},
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

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
