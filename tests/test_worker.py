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
