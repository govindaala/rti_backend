# रिपॉजिटरी पथ: rti_backend/tests/test_worker_batch.py
"""CIC-only batch worker, दो-सेकंड विराम और heartbeat के परीक्षण."""

import inspect

import pytest

from app import worker, worker_batch
from app.worker_batch import run_batch


def test_batch_worker_processes_only_cic_source_jobs_and_closes_heartbeat(monkeypatch):
    """हर job को CIC seed IDs तक सीमित रखें और heartbeat बंद करें."""
    heartbeats = []
    outcomes = iter([True, True, False])
    processed_source_ids = []

    monkeypatch.setattr(worker, "record_worker_heartbeat", heartbeats.append)
    monkeypatch.setattr(worker, "recover_stale_jobs", lambda: 3)
    monkeypatch.setattr(worker_batch, "_cic_source_ids", lambda: ["cic-source-1"])
    monkeypatch.setattr(
        worker,
        "process_one",
        lambda allowed_source_ids=None: (
            processed_source_ids.append(allowed_source_ids) or next(outcomes)
        ),
    )

    result = run_batch(max_jobs=5, idle_seconds=0)

    assert result == {
        "recovered_stale_jobs": 3,
        "processed_jobs": 2,
        "batch_limit": 5,
        "cic_source_count": 1,
    }
    assert processed_source_ids == [["cic-source-1"]] * 3
    assert heartbeats == ["running", "stopped"]


def test_cic_source_lookup_uses_only_cic_hosts(monkeypatch):
    """Queue scope query में केवल CIC के approved seed hosts रहें."""
    class FakeCursor:
        query = ""
        params = None

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            self.query = query
            self.params = params

        def fetchall(self):
            return [("source-1",), ("source-2",)]

    class FakeConnection:
        def __init__(self):
            self.fake_cursor = FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return self.fake_cursor

    connection = FakeConnection()
    monkeypatch.setattr(worker, "get_connection", lambda: connection)

    assert worker_batch._cic_source_ids() == ["source-1", "source-2"]
    assert connection.fake_cursor.params == (["cic.gov.in", "www.cic.gov.in"],)
    assert "rti.research_sources" in connection.fake_cursor.query


def test_batch_worker_defaults_to_two_second_gap():
    """अगली job से पहले default विराम ठीक दो सेकंड रहे."""
    assert inspect.signature(run_batch).parameters["idle_seconds"].default == 2


@pytest.mark.parametrize(
    ("max_jobs", "idle_seconds"),
    [(0, 2), (-1, 2), (1, -1)],
)
def test_batch_worker_rejects_invalid_limits(max_jobs, idle_seconds):
    """अमान्य batch सीमा या नकारात्मक विराम स्वीकार न हो."""
    with pytest.raises(ValueError):
        run_batch(max_jobs=max_jobs, idle_seconds=idle_seconds)
