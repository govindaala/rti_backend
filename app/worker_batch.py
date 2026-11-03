# रिपॉजिटरी पथ: rti_backend/app/worker_batch.py
"""GitHub Actions के सीमित CIC-only batch worker और process heartbeat का संचालन."""

import logging
from threading import Event, Thread

import psycopg

from app import worker

LOGGER = logging.getLogger("rti.worker_batch")
CIC_SOURCE_HOSTS = ("cic.gov.in", "www.cic.gov.in")


def _cic_source_ids() -> list[str]:
    """केवल CIC hostname वाले seed records की IDs लौटाएँ."""
    with worker.get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM rti.research_sources
            WHERE lower(
                split_part(
                    split_part(COALESCE(normalized_url, submitted_url), '://', 2),
                    '/',
                    1
                )
            ) = ANY(%s::text[])
            ORDER BY created_at ASC
            """,
            (list(CIC_SOURCE_HOSTS),),
        )
        return [str(row[0]) for row in cursor.fetchall()]


def _heartbeat_loop(stop_event: Event) -> None:
    """लंबे crawl/OCR के दौरान process heartbeat को ताज़ा रखें."""
    while not stop_event.wait(worker.HEARTBEAT_INTERVAL_SECONDS):
        try:
            worker.record_worker_heartbeat("running")
        except (psycopg.Error, RuntimeError):
            LOGGER.exception("Batch worker heartbeat could not be refreshed")


def run_batch(max_jobs: int = 5, idle_seconds: int = 2) -> dict[str, int]:
    """केवल CIC source jobs चलाएँ और हर job के बाद निर्धारित विराम रखें."""
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
    cic_source_ids: list[str] = []
    try:
        recovered = worker.recover_stale_jobs()
        cic_source_ids = _cic_source_ids()
        for index in range(max_jobs):
            if not worker.process_one(allowed_source_ids=cic_source_ids):
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
        "cic_source_count": len(cic_source_ids),
    }
