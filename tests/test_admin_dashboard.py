# रिपॉजिटरी पथ: rti_backend/tests/test_admin_dashboard.py
"""Admin login/session, dashboard authorization, and privileged API security tests."""

from dataclasses import replace
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.routes import admin as admin_routes
from app.core import admin_auth
from app.main import app

client = TestClient(app, base_url="https://testserver")


def configured_admin(monkeypatch):
    client.cookies.clear()
    configured = replace(
        admin_routes.settings,
        admin_id="root",
        admin_pass="test-password",
        admin_session_secret="x" * 48,
        database_url=None,
    )
    monkeypatch.setattr(admin_auth, "settings", configured)
    monkeypatch.setattr(
        admin_routes,
        "settings",
        configured,
    )


def test_admin_dashboard_requires_login() -> None:
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 401


def test_admin_login_creates_http_only_secure_session(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    assert response.status_code == 200
    cookie = response.cookies.get("rti_admin_session")
    assert cookie
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "secure" in response.headers["set-cookie"].lower()
    assert response.json()["csrf_token"]


def test_wrong_admin_credentials_are_rejected(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "wrong"},
    )
    assert response.status_code == 401


def test_authenticated_dashboard_works_without_database(monkeypatch) -> None:
    configured_admin(monkeypatch)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    response = client.get("/api/v1/admin/dashboard")
    assert login.status_code == 200
    assert response.status_code == 200
    assert response.json()["database"] == "not_configured"


def test_source_submission_requires_session_and_csrf(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post("/api/v1/admin/sources", json={"url": "https://cic.gov.in/"})
    assert response.status_code == 401


def test_source_submission_rejects_non_official_domain_after_login(monkeypatch) -> None:
    configured_admin(monkeypatch)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    response = client.post(
        "/api/v1/admin/sources",
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
        json={"url": "https://example.com/"},
    )
    assert response.status_code == 422


def test_document_verification_requires_authenticated_session(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post(
        "/api/v1/admin/documents/00000000-0000-0000-0000-000000000001/verify",
        json={
            "review_note": "मूल आदेश और वर्तमान स्थिति की समीक्षा की गई है।",
            "confirm_reviewed": True,
        },
    )
    assert response.status_code == 401


def test_admin_dashboard_exposes_live_ocr_backlog_metrics(monkeypatch) -> None:
    configured = replace(
        admin_routes.settings,
        admin_id="root",
        admin_pass="test-password",
        admin_session_secret="x" * 48,
        database_url="postgresql://test.invalid/db",
    )
    monkeypatch.setattr(admin_auth, "settings", configured)
    monkeypatch.setattr(admin_routes, "settings", configured)

    class FakeCursor:
        def __init__(self) -> None:
            self.fetchall_results = iter([
                [("completed", 2)],
                [("completed", 1)],
                [("review_required", 3), ("needs_ocr", 1)],
                [],
                [],
            ])
            self.fetchone_results = iter([(2, 1, 123), (1, 1, 0), (0, 0, 0, 0), (0,)])

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query, _params=None) -> None:
            return None

        def fetchall(self):
            return next(self.fetchall_results)

        def fetchone(self):
            return next(self.fetchone_results)

    class FakeConnection:
        def __init__(self) -> None:
            self.fake_cursor = FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return self.fake_cursor

    monkeypatch.setattr(admin_routes, "get_connection", lambda: FakeConnection())
    client.cookies.clear()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    assert login.status_code == 200
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["ocr_pending_documents"] == 1
    assert metrics["ocr_extracted_documents"] == 1
    assert metrics["empty_text_documents"] == 0
    assert metrics["daily_documents_found"] == 0
    assert metrics["daily_documents_read"] == 0
    assert metrics["daily_preliminary_analyses"] == 0
    assert metrics["daily_failed_jobs"] == 0


def test_ocr_retry_requires_authenticated_session(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post(
        "/api/v1/admin/documents/00000000-0000-0000-0000-000000000001/retry-ocr",
    )
    assert response.status_code == 401


def test_ocr_retry_queues_only_eligible_document_and_never_verifies(monkeypatch) -> None:
    configured = replace(
        admin_routes.settings,
        admin_id="root",
        admin_pass="test-password",
        admin_session_secret="x" * 48,
        database_url="postgresql://test.invalid/db",
    )
    monkeypatch.setattr(admin_auth, "settings", configured)
    monkeypatch.setattr(admin_routes, "settings", configured)

    class FakeCursor:
        def __init__(self) -> None:
            self.query_log = []
            self.fetchone_results = iter([
                ("source-id", "https://cic.gov.in/orders/123.pdf", "needs_ocr", True, "completed"),
                ("job-id",),
            ])

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None) -> None:
            self.query_log.append((query, params))

        def fetchone(self):
            return next(self.fetchone_results)

    class FakeConnection:
        def __init__(self) -> None:
            self.fake_cursor = FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return self.fake_cursor

    connection = FakeConnection()
    monkeypatch.setattr(admin_routes, "get_connection", lambda: connection)
    client.cookies.clear()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    response = client.post(
        "/api/v1/admin/documents/00000000-0000-0000-0000-000000000001/retry-ocr",
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
    )

    assert response.status_code == 202
    assert response.json()["queued"] is True
    assert response.json()["job_id"] == "job-id"
    assert "verified" not in response.json()
    queries = " ".join(query for query, _ in connection.fake_cursor.query_log)
    assert "ocr_retry_queued" in queries
    assert "SET status = 'discovering'" in queries


def test_ocr_retry_rejects_documents_not_waiting_for_ocr(monkeypatch) -> None:
    configured = replace(
        admin_routes.settings,
        admin_id="root",
        admin_pass="test-password",
        admin_session_secret="x" * 48,
        database_url="postgresql://test.invalid/db",
    )
    monkeypatch.setattr(admin_auth, "settings", configured)
    monkeypatch.setattr(admin_routes, "settings", configured)

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query, _params=None):
            return None

        def fetchone(self):
            return ("source-id", "https://cic.gov.in/orders/123.pdf", "review_required", False, "completed")

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(admin_routes, "get_connection", lambda: FakeConnection())
    client.cookies.clear()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    response = client.post(
        "/api/v1/admin/documents/00000000-0000-0000-0000-000000000001/retry-ocr",
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
    )
    assert response.status_code == 409


def test_queue_health_requires_login() -> None:
    client.cookies.clear()
    response = client.get("/api/v1/admin/queue-health")
    assert response.status_code == 401


def test_queue_health_reports_stalled_jobs(monkeypatch) -> None:
    configured = replace(
        admin_routes.settings,
        admin_id="root",
        admin_pass="test-password",
        admin_session_secret="x" * 48,
        database_url="postgresql://test.invalid/db",
    )
    monkeypatch.setattr(admin_auth, "settings", configured)
    monkeypatch.setattr(admin_routes, "settings", configured)

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            assert "heartbeat_at" in query
            assert "interval '10 minutes'" in query

        def fetchone(self):
            from datetime import UTC, datetime
            return (3, 1, 2, 1, 4, 1800, datetime(2026, 11, 1, tzinfo=UTC), None, 1, 0, datetime(2026, 11, 1, tzinfo=UTC))

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(admin_routes, "get_connection", lambda: FakeConnection())
    client.cookies.clear()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    assert login.status_code == 200
    response = client.get("/api/v1/admin/queue-health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["queue_health"] == "attention"
    assert payload["queued_ready"] == 3
    assert payload["queued_delayed"] == 1
    assert payload["running"] == 2
    assert payload["stale_running"] == 1
    assert payload["oldest_ready_age_seconds"] == 1800
    assert payload["failed"] == 4
    assert payload["worker_status"] == "online"
    assert payload["online_workers"] == 1
    assert payload["stale_workers"] == 0


def test_queue_health_marks_empty_queue_idle_without_database(monkeypatch) -> None:
    configured_admin(monkeypatch)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    assert login.status_code == 200
    response = client.get("/api/v1/admin/queue-health")
    assert response.status_code == 200
    assert response.json()["database"] == "not_configured"
    assert response.json()["queue_health"] == "unknown"


def test_ocr_pending_list_requires_authenticated_session(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.get("/api/v1/admin/documents/ocr-pending")
    assert response.status_code == 401


def test_ocr_pending_list_uses_bounded_pagination(monkeypatch) -> None:
    configured = replace(
        admin_routes.settings,
        admin_id="root",
        admin_pass="test-password",
        admin_session_secret="x" * 48,
        database_url="postgresql://test.invalid/db",
    )
    monkeypatch.setattr(admin_auth, "settings", configured)
    monkeypatch.setattr(admin_routes, "settings", configured)

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            assert "ocr_required = true AND status = 'needs_ocr'" in query
            assert params == (3, 10)

        def fetchall(self):
            stamp = datetime(2026, 11, 1, tzinfo=UTC)
            return [
                ("doc-1", "Scanned order A", "https://cic.gov.in/a.pdf", "needs_ocr", stamp),
                ("doc-2", "Scanned order B", "https://cic.gov.in/b.pdf", "needs_ocr", stamp),
                ("doc-3", "Scanned order C", "https://cic.gov.in/c.pdf", "needs_ocr", stamp),
            ]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(admin_routes, "get_connection", lambda: FakeConnection())
    client.cookies.clear()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    response = client.get("/api/v1/admin/documents/ocr-pending?limit=2&offset=10")

    assert login.status_code == 200
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["has_more"] is True
    assert data["offset"] == 10
    assert data["items"][0]["status"] == "needs_ocr"
    assert data["items"][0]["ocr_required"] is True


def test_queue_health_flags_ready_jobs_when_worker_heartbeat_is_stale(monkeypatch) -> None:
    configured = replace(
        admin_routes.settings,
        admin_id="root",
        admin_pass="test-password",
        admin_session_secret="x" * 48,
        database_url="postgresql://test.invalid/db",
    )
    monkeypatch.setattr(admin_auth, "settings", configured)
    monkeypatch.setattr(admin_routes, "settings", configured)

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query, _params=None):
            return None

        def fetchone(self):
            from datetime import UTC, datetime
            return (2, 0, 0, 0, 0, 30, None, None, 0, 1, datetime(2026, 11, 1, tzinfo=UTC))

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(admin_routes, "get_connection", lambda: FakeConnection())
    client.cookies.clear()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    assert login.status_code == 200
    response = client.get("/api/v1/admin/queue-health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["worker_status"] == "stale"
    assert payload["queue_health"] == "attention"
    assert payload["queued_ready"] == 2
