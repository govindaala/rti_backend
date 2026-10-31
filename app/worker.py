# रिपॉजिटरी पथ: rti_backend/app/worker.py
"""एक queued crawl job process करने वाला one-shot worker."""

import argparse
import logging
import sys

from app.core.database import get_connection
from app.services.crawler import fetch_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("rti.worker")


def process_one() -> bool:
    """एक job claim करके fetch/extract करें; उपलब्ध न हो तो False लौटाएँ."""
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT j.id, s.id, s.submitted_url
            FROM rti.crawl_jobs j
            JOIN rti.research_sources s ON s.id = j.source_id
            WHERE j.status = 'queued'
            ORDER BY j.created_at
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
            SET status='running', started_at=COALESCE(started_at, now()),
                heartbeat_at=now(), attempts=attempts+1, updated_at=now()
            WHERE id=%s
            """,
            (job_id,),
        )
        cursor.execute("UPDATE rti.research_sources SET status='discovering', updated_at=now() WHERE id=%s",
                       (source_id,))
        cursor.execute(
            "INSERT INTO rti.crawl_job_events(job_id,event_type,message) VALUES(%s,'started','Worker started source fetch')",
            (job_id,),
        )
    try:
        result = fetch_document(url)
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rti.legal_documents
                    (source_id, job_id, canonical_url, title, document_type,
                     content_type, extracted_text, content_sha256, page_count, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'review_required')
                ON CONFLICT (canonical_url) DO UPDATE SET
                    extracted_text=EXCLUDED.extracted_text,
                    content_sha256=EXCLUDED.content_sha256,
                    content_type=EXCLUDED.content_type,
                    page_count=EXCLUDED.page_count,
                    status='review_required',
                    updated_at=now()
                """,
                (source_id, job_id, result["final_url"], result["final_url"],
                 "other" if result["document_type"] == "html" else "unknown",
                 result["content_type"], result["text"], result["content_sha256"],
                 result["page_count"]),
            )
            cursor.execute(
                """
                UPDATE rti.crawl_jobs SET status='completed', discovered_count=1,
                    processed_count=1, heartbeat_at=now(), finished_at=now(), updated_at=now()
                WHERE id=%s
                """,
                (job_id,),
            )
            cursor.execute("UPDATE rti.research_sources SET status='completed', updated_at=now() WHERE id=%s",
                           (source_id,))
            cursor.execute(
                "INSERT INTO rti.crawl_job_events(job_id,event_type,message) VALUES(%s,'completed','Document extracted; awaiting human legal verification')",
                (job_id,),
            )
        LOGGER.info("Completed crawl job %s", job_id)
        return True
    except Exception as exc:
        # Raw exception is logged server-side; API responses never expose it.
        LOGGER.exception("Crawl job %s failed", job_id)
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE rti.crawl_jobs SET status='failed', failed_count=1,
                    last_error_code='FETCH_OR_EXTRACTION_FAILED',
                    finished_at=now(), updated_at=now()
                WHERE id=%s
                """,
                (job_id,),
            )
            cursor.execute(
                "UPDATE rti.research_sources SET status='failed', last_error_code='FETCH_OR_EXTRACTION_FAILED', updated_at=now() WHERE id=%s",
                (source_id,),
            )
            cursor.execute(
                "INSERT INTO rti.crawl_job_events(job_id,event_type,message) VALUES(%s,'failed','Fetch or extraction failed; inspect private server logs')",
                (job_id,),
            )
        return True


def main() -> int:
    """CLI में --once या --drain से queued jobs process करें."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="एक job process करें")
    group.add_argument("--drain", action="store_true", help="मौजूदा queue खाली होने तक process करें")
    args = parser.parse_args()
    if args.drain:
        while process_one():
            pass
    else:
        process_one()
    return 0


if __name__ == "__main__":
    sys.exit(main())
