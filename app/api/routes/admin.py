# रिपॉजिटरी पथ: rti_backend/app/api/routes/admin.py
"""Read-only live operations dashboard और token-protected source intake API."""

import hmac
from urllib.parse import urlsplit

import psycopg
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from app.core.config import settings
from app.core.database import get_connection
from app.services.source_registry import is_official_source_url

router = APIRouter(tags=["प्रशासन"])


class SourceSubmission(BaseModel):
    """प्रशासन द्वारा समीक्षा और crawl हेतु दिया गया आधिकारिक स्रोत URL."""

    url: HttpUrl
    label: str | None = Field(default=None, max_length=200)


def _require_admin(token: str | None) -> None:
    """केवल server-side secret से privileged operation अधिकृत करें."""
    expected = settings.admin_api_token
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator authorization required",
        )


@router.get("/admin/dashboard", summary="Live crawler dashboard आँकड़े")
def dashboard_summary() -> dict:
    """कुल आँकड़े और हाल के सार्वजनिक कानूनी दस्तावेज़ लौटाएँ."""
    if not settings.database_url:
        return {
            "database": "not_configured", "sources": {}, "jobs": {},
            "documents": {}, "recent_jobs": [], "recent_documents": [],
        }
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT status, count(*) FROM rti.crawl_jobs GROUP BY status")
            jobs = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute("SELECT status, count(*) FROM rti.research_sources GROUP BY status")
            sources = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute("SELECT status, count(*) FROM rti.legal_documents GROUP BY status")
            documents = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT j.id::text, j.status, j.current_url, j.discovered_count,
                       j.processed_count, j.failed_count, j.updated_at
                FROM rti.crawl_jobs j
                ORDER BY j.updated_at DESC LIMIT 10
                """
            )
            recent_jobs = [
                {
                    "id": row[0], "status": row[1], "url": row[2],
                    "discovered": row[3], "processed": row[4],
                    "failed": row[5], "updated_at": row[6].isoformat(),
                }
                for row in cursor.fetchall()
            ]
            cursor.execute(
                """
                SELECT id::text, title, canonical_url, document_type,
                       status, created_at
                FROM rti.legal_documents
                ORDER BY created_at DESC LIMIT 10
                """
            )
            recent_documents = [
                {
                    "id": row[0], "title": row[1], "url": row[2],
                    "type": row[3], "status": row[4],
                    "created_at": row[5].isoformat(),
                }
                for row in cursor.fetchall()
            ]
        return {
            "database": "connected",
            "sources": sources,
            "jobs": jobs,
            "documents": documents,
            "recent_jobs": recent_jobs,
            "recent_documents": recent_documents,
        }
    except (psycopg.Error, RuntimeError):
        return {
            "database": "unavailable", "sources": {}, "jobs": {},
            "documents": {}, "recent_jobs": [], "recent_documents": [],
        }


@router.post("/admin/sources", status_code=202, summary="कानूनी स्रोत जोड़ें और crawl queue करें")
def submit_source(
    payload: SourceSubmission,
    x_admin_token: str | None = Header(default=None),
) -> dict:
    """Allowlisted HTTPS सरकारी स्रोत को durable database queue में जोड़ें."""
    _require_admin(x_admin_token)
    submitted_url = str(payload.url)
    parsed = urlsplit(submitted_url)
    if not is_official_source_url(submitted_url):
        raise HTTPException(status_code=422, detail="केवल allowlisted HTTPS सरकारी स्रोत स्वीकार हैं")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise HTTPException(status_code=422, detail="URL में credentials या non-standard port स्वीकार नहीं")
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rti.research_sources
                    (submitted_url, normalized_url, source_label, status)
                VALUES (%s, %s, %s, 'queued')
                ON CONFLICT (normalized_url) DO UPDATE
                    SET source_label = COALESCE(EXCLUDED.source_label, rti.research_sources.source_label),
                        status = CASE
                            WHEN rti.research_sources.status = 'paused' THEN 'queued'
                            ELSE rti.research_sources.status
                        END,
                        updated_at = now()
                RETURNING id, status
                """,
                (submitted_url, submitted_url, payload.label),
            )
            source_id, source_status = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO rti.crawl_jobs (source_id, status, current_url)
                SELECT %s, 'queued', %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM rti.crawl_jobs
                    WHERE source_id=%s AND current_url=%s
                      AND status IN ('queued','running')
                )
                RETURNING id
                """,
                (source_id, submitted_url, source_id, submitted_url),
            )
            row = cursor.fetchone()
            if row:
                job_id = row[0]
                cursor.execute(
                    """
                    INSERT INTO rti.crawl_job_events (job_id, event_type, message)
                    VALUES (%s, 'queued', 'Administrator approved source for crawling')
                    """,
                    (job_id,),
                )
                queued = True
            else:
                cursor.execute(
                    """
                    SELECT id FROM rti.crawl_jobs
                    WHERE source_id=%s AND current_url=%s
                      AND status IN ('queued','running')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (source_id, submitted_url),
                )
                job_id = cursor.fetchone()[0]
                queued = False
        return {
            "accepted": True,
            "queued": queued,
            "source_id": str(source_id),
            "job_id": str(job_id),
            "source_status": source_status,
            "message": "Source is queued for background processing" if queued else "Source already queued or running",
        }
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Source queue is temporarily unavailable",
        ) from exc
