# रिपॉजिटरी पथ: rti_backend/tests/test_worker_batch.py
"""सीमित batch worker, दो-सेकंड विराम और heartbeat के परीक्षण."""

import inspect

import pytest

from app import worker
from app.worker_batch import run_batch


def test_batch_worker_processes_only_available_jobs_and_closes_heartbeat(monkeypatch):
    """उपलब्ध jobs ही चलें और batch के अंत में heartbeat stopped हो."""
    heartbeats = []
    outcomes = iter([True, True, False])

    monkeypatch.setattr(worker, "record_worker_heartbeat", heartbeats.append)
    monkeypatch.setattr(worker, "recover_stale_jobs", lambda: 3)
    monkeypatch.setattr(worker, "process_one", lambda: next(outcomes))

    result = run_batch(max_jobs=5, idle_seconds=0)

    assert result == {
        "recovered_stale_jobs": 3,
        "processed_jobs": 2,
        "batch_limit": 5,
    }
    assert heartbeats == ["running", "stopped"]


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
