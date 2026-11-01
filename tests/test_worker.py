# रिपॉजिटरी पथ: rti_backend/tests/test_worker.py
"""Continuous worker loop और graceful stop के unit tests."""

import sys
from types import SimpleNamespace

import httpx

from app import worker


def test_worker_stops_cleanly_after_shutdown_signal(monkeypatch) -> None:
    """SIGTERM flag set होने पर worker अगला polling cycle नहीं चलाता."""
    worker.STOP.clear()
    # Worker loop के database recovery चरण को isolate करें; यह unit test है.
    monkeypatch.setattr(worker, "recover_stale_jobs", lambda: 0)

    def fake_process_one() -> bool:
        worker.STOP.set()
        return False

    monkeypatch.setattr(worker, "process_one", fake_process_one)
    monkeypatch.setattr(worker, "enqueue_due_source", lambda: False)
    worker.run_worker(poll_seconds=0, idle_seconds=0)
    assert worker.STOP.is_set()
    worker.STOP.clear()


def test_worker_schedules_due_source_when_queue_is_empty(monkeypatch) -> None:
    """Queue खाली होने पर due-source scheduler चलता है और नई job process होती है."""
    worker.STOP.clear()
    monkeypatch.setattr(worker, "recover_stale_jobs", lambda: 0)
    calls = {"process": 0, "schedule": 0}

    def fake_process_one() -> bool:
        calls["process"] += 1
        if calls["process"] == 2:
            worker.STOP.set()
            return True
        return False

    def fake_enqueue_due_source() -> bool:
        calls["schedule"] += 1
        return True

    monkeypatch.setattr(worker, "process_one", fake_process_one)
    monkeypatch.setattr(worker, "enqueue_due_source", fake_enqueue_due_source)
    worker.run_worker(poll_seconds=0, idle_seconds=0)
    assert calls == {"process": 2, "schedule": 1}
    worker.STOP.clear()


def test_retry_policy_only_retries_transient_failures() -> None:
    """Network errors and selected transient HTTP statuses retry; 404 does not."""
    assert worker._is_retryable_error(httpx.ConnectError("temporary"))
    request = httpx.Request("GET", "https://cic.gov.in/")
    transient = httpx.Response(503, request=request)
    permanent = httpx.Response(404, request=request)
    assert worker._is_retryable_error(
        httpx.HTTPStatusError("temporary", request=request, response=transient)
    )
    assert not worker._is_retryable_error(
        httpx.HTTPStatusError("not found", request=request, response=permanent)
    )
    assert not worker._is_retryable_error(ValueError("unsupported type"))


def test_retry_delay_uses_bounded_exponential_backoff() -> None:
    """Transient failures को bounded delay मिले; retry storm न बने."""
    assert worker._retry_delay_seconds(1) == 30
    assert worker._retry_delay_seconds(2) == 60
    assert worker._retry_delay_seconds(3) == 120
    assert worker._retry_delay_seconds(20) == 1800


def test_recover_stale_jobs_uses_database_lease_timeout(monkeypatch) -> None:
    """Worker crash के बाद stale running jobs की recovery query execute हो."""
    class FakeCursor:
        def __init__(self) -> None:
            self.query = ""
            self.params = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params=None) -> None:
            self.query = query
            self.params = params

        def fetchone(self):
            return (2,)

    class FakeConnection:
        def __init__(self) -> None:
            self.fake_cursor = FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return self.fake_cursor

    connection = FakeConnection()
    monkeypatch.setattr(worker, "get_connection", lambda: connection)

    assert worker.recover_stale_jobs(stale_after_seconds=90) == 2
    assert connection.fake_cursor.params == (90,)
    assert "WORKER_LEASE_EXPIRED" in connection.fake_cursor.query
    assert "status = 'running'" in connection.fake_cursor.query


def test_ocr_required_document_is_not_marked_review_ready() -> None:
    assert worker.document_status_for_extraction(True) == "needs_ocr"


def test_text_extracted_document_remains_human_review_required() -> None:
    assert worker.document_status_for_extraction(False) == "review_required"


def test_preflight_fails_when_database_url_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(worker, "settings", SimpleNamespace(database_url=None))
    monkeypatch.setattr(
        worker,
        "get_connection",
        lambda: (_ for _ in ()).throw(AssertionError("database should not be opened")),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(get_languages=lambda config="": ["eng", "hin"]),
    )

    report = worker.preflight()

    assert report["ok"] is False
    assert report["database_configured"] is False
    assert "DATABASE_URL is not configured" in report["errors"]


def test_preflight_checks_required_schema_and_ocr_languages(monkeypatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query, _params=None):
            return None

        def fetchone(self):
            return (True, True, True, True, True, True)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(
        worker, "settings", SimpleNamespace(database_url="postgresql://test.invalid/db")
    )
    monkeypatch.setattr(worker, "get_connection", lambda: FakeConnection())
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(get_languages=lambda config="": ["eng", "hin"]),
    )

    report = worker.preflight()

    assert report["ok"] is True
    assert report["database_schema_ready"] is True
    assert report["ocr_ready"] is True
    assert report["missing_ocr_languages"] == []


def test_preflight_keeps_worker_usable_when_ocr_runtime_is_missing(monkeypatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query, _params=None):
            return None

        def fetchone(self):
            return (True, True, True, True, True, True)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    def missing_tesseract(config=""):
        raise RuntimeError("tesseract binary missing")

    monkeypatch.setattr(
        worker, "settings", SimpleNamespace(database_url="postgresql://test.invalid/db")
    )
    monkeypatch.setattr(worker, "get_connection", lambda: FakeConnection())
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(get_languages=missing_tesseract),
    )

    report = worker.preflight()

    assert report["ok"] is True
    assert report["database_schema_ready"] is True
    assert report["ocr_ready"] is False
    assert report["warnings"]


def test_record_worker_heartbeat_upserts_running_status(monkeypatch) -> None:
    statements = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            statements.append((query, params))

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(worker, "get_connection", lambda: FakeConnection())
    worker.record_worker_heartbeat("running")
    assert len(statements) == 1
    assert "INSERT INTO rti.worker_heartbeats" in statements[0][0]
    assert "ON CONFLICT (worker_id)" in statements[0][0]
    assert statements[0][1][3] == "running"


def test_record_worker_heartbeat_rejects_unknown_status() -> None:
    import pytest

    with pytest.raises(ValueError):
        worker.record_worker_heartbeat("healthy")
