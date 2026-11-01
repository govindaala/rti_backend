# रिपॉजिटरी पथ: rti_backend/app/worker.py
"""लगातार चलने वाला, queue-backed सरकारी कानूनी दस्तावेज़ crawler worker."""

import argparse
import json
import logging
import signal
import sys
from threading import Event

import httpx
import psycopg

from app.core.config import settings
from app.core.database import get_connection
from app.services.crawler import (classify_document_type, discover_legal_links, discover_sitemap_links, fetch_document)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("rti.worker")
STOP = Event()


def document_status_for_extraction(ocr_required: bool) -> str:
    """OCR बाकी हो तो दस्तावेज़ को review-ready न मानकर अलग queue state दें."""
    return "needs_ocr" if ocr_required else "review_required"


def _retry_delay_seconds(attempts: int) -> int:
    """बार-बार विफल स्रोतों पर exponential backoff लागू करें."""
    return min(30 * (2 ** min(max(attempts - 1, 0), 6)), 1800)


def _is_retryable_error(error: Exception) -> bool:
    """केवल transient network/HTTP failures को सीमित retry दें."""
    if isinstance(error, httpx.TransportError):
        return True
    return (
        isinstance(error, httpx.HTTPStatusError)
        and error.response.status_code in {408, 425, 429, 500, 502, 503, 504}
    )


def _stop_worker(signum: int, frame: object) -> None:
    """Render shutdown signal पर worker को graceful stop करें."""
    LOGGER.info("Shutdown signal received: %s", signum)
    STOP.set()


def enqueue_due_source() -> bool:
    """हर configured interval के बाद completed source को दोबारा crawl queue करें."""
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT s.id, s.submitted_url
            FROM rti.research_sources s
            WHERE s.status = 'completed'
              AND s.updated_at <= now() - make_interval(hours => %s)
              AND NOT EXISTS (
                SELECT 1 FROM rti.crawl_jobs j
                WHERE j.source_id=s.id AND j.status IN ('queued','running')
              )
            ORDER BY s.updated_at ASC
            FOR UPDATE OF s SKIP LOCKED
            LIMIT 1
            """,
            (settings.crawler_recrawl_hours,),
        )
        row = cursor.fetchone()
        if not row:
            return False
        source_id, source_url = row
        cursor.execute(
            """
            UPDATE rti.research_sources
            SET status='queued', updated_at=now(), last_error_code=NULL
            WHERE id=%s
            """,
            (source_id,),
        )
        cursor.execute(
            """
            INSERT INTO rti.crawl_jobs (source_id, status, current_url)
            VALUES (%s, 'queued', %s)
            RETURNING id
            """,
            (source_id, source_url),
        )
        job_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO rti.crawl_job_events(job_id,event_type,message)
            VALUES(%s,'scheduled','Periodic source re-crawl scheduled')
            """,
            (job_id,),
        )
    LOGGER.info("Scheduled periodic re-crawl source=%s job=%s", source_id, job_id)
    return True


def recover_stale_jobs(stale_after_seconds: int = 300) -> int:
    """Crash हुए worker की lease समाप्त jobs को retry queue में वापस रखें."""
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            WITH recovered AS (
                UPDATE rti.crawl_jobs
                SET status = CASE WHEN attempts < max_attempts THEN 'queued' ELSE 'failed' END,
                    available_at = CASE
                        WHEN attempts < max_attempts THEN now() + interval '30 seconds'
                        ELSE available_at
                    END,
                    finished_at = CASE
                        WHEN attempts < max_attempts THEN NULL ELSE now()
                    END,
                    failed_count = CASE
                        WHEN attempts < max_attempts THEN failed_count ELSE 1
                    END,
                    last_error_code = 'WORKER_LEASE_EXPIRED',
                    updated_at = now()
                WHERE status = 'running'
                  AND COALESCE(heartbeat_at, started_at, created_at)
                      < now() - make_interval(secs => %s)
                RETURNING id, source_id, status
            ),
            event_rows AS (
                INSERT INTO rti.crawl_job_events (job_id, event_type, message)
                SELECT id, 'lease_recovered',
                       CASE WHEN status = 'queued'
                           THEN 'Worker lease expired; job returned to retry queue'
                           ELSE 'Worker lease expired; retry limit exhausted'
                       END
                FROM recovered
                RETURNING job_id
            ),
            source_rows AS (
                UPDATE rti.research_sources AS source
                SET status = CASE
                        WHEN EXISTS (
                            SELECT 1 FROM rti.crawl_jobs AS job
                            WHERE job.source_id = source.id
                              AND job.status IN ('queued', 'running')
                              AND NOT EXISTS (
                                  SELECT 1 FROM recovered AS item WHERE item.id = job.id
                              )
                        ) OR EXISTS (
                            SELECT 1 FROM recovered AS item
                            WHERE item.source_id = source.id AND item.status = 'queued'
                        ) THEN 'discovering'
                        ELSE 'failed'
                    END,
                    last_error_code = 'WORKER_LEASE_EXPIRED',
                    updated_at = now()
                WHERE source.id IN (SELECT source_id FROM recovered)
                RETURNING source.id
            )
            SELECT count(*) FROM recovered
            """,
            (stale_after_seconds,),
        )
        recovered_count = cursor.fetchone()[0]
    if recovered_count:
        LOGGER.warning("Recovered %s stale crawler jobs", recovered_count)
    return recovered_count


def process_one() -> bool:
    """एक job atomically claim करके fetch, extract और child links queue करें."""
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT j.id, s.id, COALESCE(j.current_url, s.submitted_url)
            FROM rti.crawl_jobs j
            JOIN rti.research_sources s ON s.id = j.source_id
            WHERE j.status = 'queued' AND j.available_at <= now()
            ORDER BY j.available_at, j.created_at
            FOR UPDATE OF j SKIP LOCKED
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return False
        job_id, source_id, url = row
        cursor.execute(
            """
            UPDATE rti.crawl_jobs
            SET status='running', current_url=%s,
                started_at=COALESCE(started_at, now()),
                heartbeat_at=now(), attempts=attempts+1, updated_at=now()
            WHERE id=%s
            """,
            (url, job_id),
        )
        cursor.execute(
            "UPDATE rti.research_sources SET status='discovering' WHERE id=%s",
            (source_id,),
        )
        cursor.execute(
            """
            INSERT INTO rti.crawl_job_events(job_id,event_type,message)
            VALUES(%s,'started','Worker started an approved source URL')
            """,
            (job_id,),
        )

    try:
        result = fetch_document(
            url,
            timeout_seconds=settings.crawler_timeout_seconds,
            max_bytes=settings.crawler_max_bytes,
        )
        child_links = []
        if result["document_type"] == "html" and result["html"]:
            child_links.extend(
                discover_legal_links(result["html"], result["final_url"], settings.crawler_links_per_page)
            )
            try:
                child_links.extend(
                    discover_sitemap_links(
                        result["final_url"],
                        timeout_seconds=settings.crawler_timeout_seconds,
                        max_urls=settings.crawler_links_per_page * 4,
                    )
                )
            except Exception:
                LOGGER.exception("Sitemap discovery failed for source=%s", source_id)
        child_links = list(dict.fromkeys(child_links))
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rti.legal_documents
                    (source_id, job_id, canonical_url, title, document_type,
                     content_type, extracted_text, content_sha256, page_count,
                     extraction_status, ocr_required, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (canonical_url) DO UPDATE SET
                    source_id=EXCLUDED.source_id,
                    job_id=EXCLUDED.job_id,
                    title=EXCLUDED.title,
                    extracted_text=EXCLUDED.extracted_text,
                    content_type=EXCLUDED.content_type,
                    page_count=EXCLUDED.page_count,
                    extraction_status=EXCLUDED.extraction_status,
                    ocr_required=EXCLUDED.ocr_required,
                    status=CASE
                        WHEN EXCLUDED.ocr_required THEN 'needs_ocr'
                        WHEN rti.legal_documents.status = 'needs_ocr'
                             AND EXCLUDED.extraction_status IN ('extracted', 'extracted_ocr')
                        THEN 'review_required'
                        WHEN rti.legal_documents.content_sha256
                             IS DISTINCT FROM EXCLUDED.content_sha256
                        THEN 'review_required'
                        ELSE rti.legal_documents.status
                    END,
                    review_note=CASE
                        WHEN EXCLUDED.ocr_required OR
                             rti.legal_documents.content_sha256
                             IS DISTINCT FROM EXCLUDED.content_sha256
                        THEN NULL
                        ELSE rti.legal_documents.review_note
                    END,
                    verified_at=CASE
                        WHEN EXCLUDED.ocr_required OR
                             rti.legal_documents.content_sha256
                             IS DISTINCT FROM EXCLUDED.content_sha256
                        THEN NULL
                        ELSE rti.legal_documents.verified_at
                    END,
                    content_sha256=EXCLUDED.content_sha256,
                    updated_at=now()
                """,
                (
                    source_id, job_id, result["final_url"], result["title"],
                    classify_document_type(url, result["title"], result["text"]),
                    result["content_type"], result["text"], result["content_sha256"],
                    result["page_count"], result["extraction_status"], result["ocr_required"],
                    document_status_for_extraction(result["ocr_required"]),
                ),
            )

            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (str(source_id),))
            cursor.execute(
                """
                SELECT count(*) FROM rti.crawl_jobs
                WHERE source_id=%s
                  AND created_at >= (
                    SELECT updated_at FROM rti.research_sources WHERE id=%s
                  )
                  AND status IN ('queued','running','completed')
                """,
                (source_id, source_id),
            )
            existing_jobs = cursor.fetchone()[0]
            remaining_budget = max(0, settings.crawler_max_pages_per_source - existing_jobs)
            queued_links = 0
            for child_url in child_links[:remaining_budget]:
                cursor.execute(
                    """
                    INSERT INTO rti.crawl_jobs (source_id, status, current_url)
                    SELECT %s, 'queued', %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM rti.crawl_jobs
                        WHERE source_id=%s AND current_url=%s
                          AND created_at >= (
                            SELECT updated_at FROM rti.research_sources WHERE id=%s
                          )
                          AND status IN ('queued','running','completed')
                    )
                    """,
                    (source_id, child_url, source_id, child_url, source_id),
                )
                queued_links += cursor.rowcount

            cursor.execute(
                """
                UPDATE rti.crawl_jobs SET status='completed',
                    discovered_count=%s, processed_count=1, failed_count=0,
                    last_error_code=NULL, heartbeat_at=now(),
                    finished_at=now(), updated_at=now()
                WHERE id=%s
                """,
                (queued_links, job_id),
            )
            cursor.execute(
                """
                INSERT INTO rti.crawl_job_events(job_id,event_type,message)
                VALUES(%s,'completed',%s)
                """,
                (
                    job_id,
                    (
                        "Fetched document; OCR remains required; "
                        if result["ocr_required"]
                        else "Extracted document; "
                    )
                    + f"queued {queued_links} allowlisted official legal, pagination and sitemap links; human review required",
                ),
            )
            cursor.execute(
                """
                SELECT count(*) FROM rti.crawl_jobs
                WHERE source_id=%s AND status IN ('queued','running')
                """,
                (source_id,),
            )
            pending = cursor.fetchone()[0]
            cursor.execute(
                """
                UPDATE rti.research_sources
                SET status=%s,
                    last_error_code=CASE WHEN %s='completed' THEN NULL ELSE last_error_code END,
                    updated_at=CASE WHEN %s='completed' THEN now() ELSE updated_at END
                WHERE id=%s
                """,
                (
                    "discovering" if pending else "completed",
                    "discovering" if pending else "completed",
                    "discovering" if pending else "completed",
                    source_id,
                ),
            )
        LOGGER.info(
            "Completed job=%s source=%s child_links=%s",
            job_id, source_id, queued_links,
        )
        return True
    except Exception as exc:
        LOGGER.exception("Crawl job %s failed", job_id)
        error_code = (
            "ROBOTS_DISALLOWED" if isinstance(exc, PermissionError)
            else "FETCH_OR_EXTRACTION_FAILED"
        )
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT attempts, max_attempts FROM rti.crawl_jobs WHERE id=%s",
                (job_id,),
            )
            attempts, max_attempts = cursor.fetchone()
            if _is_retryable_error(exc) and attempts < max_attempts:
                cursor.execute(
                    """
                    UPDATE rti.crawl_jobs SET status='queued',
                        available_at=now() + make_interval(secs => %s),
                        last_error_code='TRANSIENT_FETCH_ERROR',
                        finished_at=NULL, heartbeat_at=now(), updated_at=now()
                    WHERE id=%s
                    """,
                    (_retry_delay_seconds(attempts), job_id),
                )
                cursor.execute(
                    """
                    INSERT INTO rti.crawl_job_events(job_id,event_type,message)
                    VALUES(%s,'retry','Transient fetch failure; job returned to queue')
                    """,
                    (job_id,),
                )
                cursor.execute(
                    "UPDATE rti.research_sources SET status='discovering' WHERE id=%s",
                    (source_id,),
                )
                return True
            cursor.execute(
                """
                UPDATE rti.crawl_jobs SET status='failed', failed_count=1,
                    last_error_code=%s, heartbeat_at=now(),
                    finished_at=now(), updated_at=now()
                WHERE id=%s
                """,
                (error_code, job_id),
            )
            cursor.execute(
                """
                INSERT INTO rti.crawl_job_events(job_id,event_type,message)
                VALUES(%s,'failed',%s)
                """,
                (job_id, error_code),
            )
            cursor.execute(
                """
                UPDATE rti.research_sources SET status='failed',
                    last_error_code=%s, updated_at=now()
                WHERE id=%s
                  AND NOT EXISTS (
                    SELECT 1 FROM rti.crawl_jobs
                    WHERE source_id=%s AND status IN ('queued','running')
                  )
                """,
                (error_code, source_id, source_id),
            )
        return True



def preflight() -> dict:
    """Deployment से पहले database schema और optional OCR runtime की readiness जाँचें."""
    report = {
        "ok": False,
        "database_configured": bool(settings.database_url),
        "database_schema_ready": False,
        "ocr_ready": False,
        "missing_ocr_languages": ["eng", "hin"],
        "warnings": [],
        "errors": [],
    }
    if not settings.database_url:
        report["errors"].append("DATABASE_URL is not configured")
    else:
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT
                           to_regclass('rti.research_sources') IS NOT NULL,
                           to_regclass('rti.crawl_jobs') IS NOT NULL,
                           to_regclass('rti.legal_documents') IS NOT NULL,
                           to_regclass('rti.crawl_job_events') IS NOT NULL,
                           EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_schema='rti' AND table_name='legal_documents'
                                     AND column_name='extraction_status'),
                           EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_schema='rti' AND table_name='legal_documents'
                                     AND column_name='ocr_required')"""
                )
                schema_checks = cursor.fetchone()
            report["database_schema_ready"] = bool(schema_checks and all(schema_checks))
            if not report["database_schema_ready"]:
                report["errors"].append(
                    "Required rti tables or OCR extraction-state columns are missing"
                )
        except (psycopg.Error, RuntimeError) as exc:
            LOGGER.exception("Worker preflight database check failed")
            report["errors"].append(f"Database preflight failed: {type(exc).__name__}")

    try:
        import pytesseract

        languages = set(pytesseract.get_languages(config=""))
        missing = sorted({"eng", "hin"} - languages)
        report["missing_ocr_languages"] = missing
        report["ocr_ready"] = not missing
    except (ImportError, OSError, RuntimeError) as exc:
        LOGGER.warning("OCR runtime unavailable during preflight: %s", type(exc).__name__)
        report["missing_ocr_languages"] = ["eng", "hin"]
        report["warnings"].append(f"OCR runtime unavailable: {type(exc).__name__}")

    if not report["ocr_ready"] and not report["warnings"]:
        report["warnings"].append("Tesseract must provide both eng and hin languages for OCR")
    report["ok"] = report["database_schema_ready"]
    return report

def run_worker(poll_seconds: int, idle_seconds: int) -> None:
    """Queue खाली होने पर भी लगातार poll करें; graceful shutdown समर्थित."""
    LOGGER.info("Continuous crawler worker started")
    while not STOP.is_set():
        try:
            recover_stale_jobs()
            processed = process_one()
            if not processed and enqueue_due_source():
                processed = process_one()
            if processed:
                STOP.wait(poll_seconds)
            else:
                STOP.wait(idle_seconds)
        except Exception:
            LOGGER.exception("Worker loop failed; retrying after idle interval")
            STOP.wait(idle_seconds)
    LOGGER.info("Crawler worker stopped cleanly")


def main() -> int:
    """CLI में --check, --once या --poll से worker चलाएँ."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Database schema और OCR readiness जाँचें")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="एक job process करें")
    group.add_argument("--poll", action="store_true", help="लगातार queue poll करें")
    parser.add_argument("--poll-seconds", type=int, default=settings.crawler_poll_seconds)
    parser.add_argument("--idle-seconds", type=int, default=settings.crawler_idle_seconds)
    args = parser.parse_args()
    if args.check:
        report = preflight()
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["ok"] else 1
    if args.poll:
        signal.signal(signal.SIGTERM, _stop_worker)
        signal.signal(signal.SIGINT, _stop_worker)
        run_worker(args.poll_seconds, args.idle_seconds)
    else:
        process_one()
    return 0


if __name__ == "__main__":
    sys.exit(main())
