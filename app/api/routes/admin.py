# रिपॉजिटरी पथ: rti_backend/app/api/routes/admin.py
"""सार्वजनिक read-only dashboard और सुरक्षित source intake API."""

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
    """प्रशासन द्वारा समीक्षा हेतु दिया गया आधिकारिक स्रोत URL."""

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


@router.get("/admin/dashboard", summary="सार्वजनिक read-only dashboard आँकड़े")
def dashboard_summary() -> dict:
    """केवल aggregate counts दें; कोई व्यक्तिगत या संवेदनशील रिकॉर्ड नहीं."""
    if not settings.database_url:
        return {"database": "not_configured", "sources": 0, "jobs": {}, "documents": {}}
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT status, count(*) FROM rti.crawl_jobs GROUP BY status")
            jobs = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute("SELECT status, count(*) FROM rti.research_sources GROUP BY status")
            sources = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute("SELECT status, count(*) FROM rti.legal_documents GROUP BY status")
            documents = {row[0]: row[1] for row in cursor.fetchall()}
        return {
            "database": "connected",
            "sources": sources,
            "jobs": jobs,
            "documents": documents,
        }
    except (psycopg.Error, RuntimeError):
        return {"database": "unavailable", "sources": {}, "jobs": {}, "documents": {}}


@router.post("/admin/sources", status_code=202, summary="नया कानूनी स्रोत कतार में जोड़ें")
def submit_source(
    payload: SourceSubmission,
    x_admin_token: str | None = Header(default=None),
) -> dict:
    """सत्यापित HTTPS सरकारी domain को source और crawl job के रूप में queue करें."""
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
                        updated_at = now()
                RETURNING id, status
                """,
                (submitted_url, submitted_url, payload.label),
            )
            source_id, source_status = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO rti.crawl_jobs (source_id, status)
                VALUES (%s, 'queued')
                RETURNING id
                """,
                (source_id,),
            )
            job_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO rti.crawl_job_events (job_id, event_type, message)
                VALUES (%s, 'queued', 'Source submitted for review and crawl')
                """,
                (job_id,),
            )
        return {
            "accepted": True,
            "source_id": str(source_id),
            "job_id": str(job_id),
            "source_status": source_status,
        }
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Source queue is temporarily unavailable",
        ) from exc
