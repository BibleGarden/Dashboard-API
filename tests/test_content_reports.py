from datetime import datetime, timezone

from fastapi.testclient import TestClient

import content_reports
import utc_time
from app.main import app
from models import RecentRequestRowModel


class FakeCursor:
    def __init__(self, rows, rowcount=1):
        self.rows = rows
        self.rowcount = rowcount
        self.sql = None
        self.params = None
        self.closed = False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, rows, rowcount=1):
        self.cursor_instance = FakeCursor(rows, rowcount=rowcount)
        self.closed = False
        self.committed = False
        self.rolled_back = False

    def cursor(self, dictionary=False):
        assert dictionary is True
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_content_reports_requires_admin_auth():
    response = TestClient(app).get("/api/content-reports")

    assert response.status_code == 401


def test_content_reports_returns_newest_first(monkeypatch, admin_headers):
    monkeypatch.setattr(utc_time, "DB_TIME_ZONE", "Europe/Moscow")
    created_at = datetime(2026, 9, 19, 9, 30)
    connection = FakeConnection(
        [
            {
                "id": 2,
                "content_type": "scripture",
                "content_text": "Psalm 23",
                "user_comment": None,
                "language": "en",
                "status": "unreviewed",
                "created_at": created_at,
            }
        ]
    )
    monkeypatch.setattr(content_reports, "create_connection", lambda: connection)

    response = TestClient(app).get(
        "/api/content-reports?limit=25",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": 2,
                "content_type": "scripture",
                "content_text": "Psalm 23",
                "user_comment": None,
                "language": "en",
                "status": "unreviewed",
                "created_at": "2026-09-19T06:30:00Z",
            }
        ],
        "count": 1,
    }
    assert "ORDER BY id DESC" in connection.cursor_instance.sql
    assert connection.cursor_instance.params == (25,)
    assert connection.cursor_instance.closed is True
    assert connection.closed is True


def test_recent_request_serializes_utc_instant(monkeypatch):
    monkeypatch.setattr(utc_time, "DB_TIME_ZONE", "UTC")
    row = RecentRequestRowModel(
        id=1, endpoint="/api/books", application="bible-garden", method="GET",
        status_code=200, response_time_ms=10, client_pseudonym="a" * 40,
        user_agent=None, created_at=datetime(2026, 9, 26, 9, 30),
    )
    assert row.model_dump(mode="json")["created_at"] == "2026-09-26T09:30:00Z"


def test_mysql_timestamp_contract_rejects_aware_datetime():
    try:
        utc_time.mysql_datetime_as_utc(datetime(2026, 9, 26, tzinfo=timezone.utc))
    except ValueError as exc:
        assert "must be naive" in str(exc)
    else:
        raise AssertionError("aware timestamp was accepted")


def test_content_reports_after_id_is_oldest_first(monkeypatch, admin_headers):
    connection = FakeConnection([])
    monkeypatch.setattr(content_reports, "create_connection", lambda: connection)

    response = TestClient(app).get(
        "/api/content-reports?after_id=41&limit=100",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "WHERE id > %s" in connection.cursor_instance.sql
    assert "ORDER BY id ASC" in connection.cursor_instance.sql
    assert connection.cursor_instance.params == (41, 100)


def test_content_reports_before_id_is_newest_first(monkeypatch, admin_headers):
    connection = FakeConnection([])
    monkeypatch.setattr(content_reports, "create_connection", lambda: connection)

    response = TestClient(app).get(
        "/api/content-reports?before_id=41&limit=10",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "WHERE id < %s" in connection.cursor_instance.sql
    assert "ORDER BY id DESC" in connection.cursor_instance.sql
    assert connection.cursor_instance.params == (41, 10)


def test_content_reports_filters_by_status_with_cursor(monkeypatch, admin_headers):
    connection = FakeConnection([])
    monkeypatch.setattr(content_reports, "create_connection", lambda: connection)

    response = TestClient(app).get(
        "/api/content-reports?status=needs_investigation&before_id=41&limit=10",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "WHERE status = %s AND id < %s" in connection.cursor_instance.sql
    assert connection.cursor_instance.params == ("needs_investigation", 41, 10)


def test_content_reports_rejects_unknown_status(admin_headers):
    response = TestClient(app).get(
        "/api/content-reports?status=unknown",
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_content_reports_rejects_two_cursors(admin_headers):
    response = TestClient(app).get(
        "/api/content-reports?after_id=1&before_id=2",
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "after_id and before_id are mutually exclusive"


def test_content_reports_fails_when_storage_is_unavailable(monkeypatch, admin_headers):
    monkeypatch.setattr(content_reports, "create_connection", lambda: None)

    response = TestClient(app).get(
        "/api/content-reports",
        headers=admin_headers,
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Content report storage is unavailable"


def test_content_report_status_rejects_invalid_admin_auth():
    response = TestClient(app).patch(
        "/api/content-reports/7/status",
        json={"status": "action_taken"},
        headers={"Authorization": "Bearer invalid"},
    )

    assert response.status_code == 401


def test_content_report_status_is_updated(monkeypatch, admin_headers):
    connection = FakeConnection([])
    monkeypatch.setattr(content_reports, "create_connection", lambda: connection)

    response = TestClient(app).patch(
        "/api/content-reports/7/status",
        json={"status": "action_taken"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"id": 7, "status": "action_taken"}
    assert "UPDATE cep_public.ai_content_reports" in connection.cursor_instance.sql
    assert connection.cursor_instance.params == ("action_taken", 7)
    assert connection.committed is True
    assert connection.rolled_back is False


def test_content_report_status_returns_404_for_unknown_report(
    monkeypatch, admin_headers
):
    connection = FakeConnection([], rowcount=0)
    monkeypatch.setattr(content_reports, "create_connection", lambda: connection)

    response = TestClient(app).patch(
        "/api/content-reports/999/status",
        json={"status": "not_significant"},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Content report not found"
    assert connection.committed is False
    assert connection.rolled_back is True


def test_content_report_status_rejects_unknown_value(admin_headers):
    response = TestClient(app).patch(
        "/api/content-reports/7/status",
        json={"status": "unknown"},
        headers=admin_headers,
    )

    assert response.status_code == 422
