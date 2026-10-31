# रिपॉजिटरी पथ: rti_backend/tests/test_worker.py
"""Continuous worker loop और graceful stop के unit tests."""

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
