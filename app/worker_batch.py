# रिपॉजिटरी पथ: rti_backend/app/worker_batch.py
"""GitHub Actions के सीमित batch worker और process heartbeat का संचालन."""

import logging
from threading import Event, Thread

import psycopg

from app import worker

LOGGER = logging.getLogger("rti.worker_batch")


def _heartbeat_loop(stop_event: Event) -> None:
    """लंबे crawl/OCR के दौरान process heartbeat को ताज़ा रखें."""
    while not stop_event.wait(worker.HEARTBEAT_INTERVAL_SECONDS):
        try:
            worker.record_worker_heartbeat("running")
        except (psycopg.Error, RuntimeError):
            LOGGER.exception("Batch worker heartbeat could not be refreshed")


def run_batch(max_jobs: int = 5, idle_seconds: int = 2) -> dict[str, int]:
    """अधिकतम jobs चलाएँ और प्रत्येक job के बाद निर्धारित विराम रखें."""
    if max_jobs < 1:
        raise ValueError("max_jobs must be at least 1")
    if idle_seconds < 0:
        raise ValueError("idle_seconds cannot be negative")

    worker.record_worker_heartbeat("running")
    stop_event = Event()
    heartbeat_thread = Thread(
        target=_heartbeat_loop,
        args=(stop_event,),
        name="batch-worker-heartbeat",
        daemon=True,
    )
    heartbeat_thread.start()

    recovered = 0
    processed = 0
    try:
        recovered = worker.recover_stale_jobs()
        for index in range(max_jobs):
            if not worker.process_one():
                break
            processed += 1
            if index + 1 < max_jobs and idle_seconds:
                stop_event.wait(idle_seconds)
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=worker.HEARTBEAT_INTERVAL_SECONDS + 5)
        try:
            worker.record_worker_heartbeat("stopped")
        except (psycopg.Error, RuntimeError):
            LOGGER.exception("Batch worker could not persist its stopped heartbeat")

    return {
        "recovered_stale_jobs": recovered,
        "processed_jobs": processed,
        "batch_limit": max_jobs,
    }
