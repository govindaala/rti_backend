# रिपॉजिटरी पथ: rti_backend/tests/test_worker.py
"""Continuous worker loop और graceful stop के unit tests."""

import httpx

from app import worker


def test_worker_stops_cleanly_after_shutdown_signal(monkeypatch) -> None:
    """SIGTERM flag set होने पर worker अगला polling cycle नहीं चलाता."""
    worker.STOP.clear()

    def fake_process_one() -> bool:
        worker.STOP.set()
        return False

    monkeypatch.setattr(worker, "process_one", fake_process_one)
    worker.run_worker(poll_seconds=0, idle_seconds=0)
    assert worker.STOP.is_set()
    worker.STOP.clear()


def test_worker_schedules_due_source_when_queue_is_empty(monkeypatch) -> None:
    """Queue खाली होने पर due-source scheduler चलता है और नई job process होती है."""
    worker.STOP.clear()
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
