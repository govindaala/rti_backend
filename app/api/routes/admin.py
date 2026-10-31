# रिपॉजिटरी पथ: rti_backend/app/api/routes/admin.py
"""Read-only live operations dashboard और token-protected source intake API."""

import hmac
from urllib.parse import urlsplit

import psycopg
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.core.config import settings
from app.core.database import get_connection
from app.services.source_registry import is_official_source_url

router = APIRouter(tags=["प्रशासन"])


class DocumentVerification(BaseModel):
    """मानव reviewer द्वारा कानूनी दस्तावेज़ सत्यापन की पुष्टि."""

    review_note: str = Field(min_length=20, max_length=1200)
    confirm_reviewed: bool

    @model_validator(mode="after")
    def require_explicit_confirmation(self) -> "DocumentVerification":
        """सिर्फ स्पष्ट reviewer confirmation पर document verified हो."""
        if not self.confirm_reviewed:
            raise ValueError("दस्तावेज़ की वास्तविक समीक्षा की पुष्टि आवश्यक है")
        self.review_note = self.review_note.strip()
        if len(self.review_note) < 20:
            raise ValueError("समीक्षा टिप्पणी कम से कम 20 अक्षरों की होनी चाहिए")
        return self


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
                SELECT id::text, job_id::text, title, canonical_url, document_type,
                       status, created_at
                FROM rti.legal_documents
                ORDER BY created_at DESC LIMIT 10
                """
            )
            recent_documents = [
                {
                    "id": row[0], "job_id": row[1], "title": row[2], "url": row[3],
                    "type": row[4], "status": row[5],
                    "created_at": row[6].isoformat(),
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
                        updated_at = CASE
                            WHEN rti.research_sources.status = 'paused' THEN now()
                            ELSE rti.research_sources.updated_at
                        END
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



@router.post(
    "/admin/documents/{document_id}/verify",
    summary="मानव समीक्षा के बाद कानूनी दस्तावेज़ verified करें",
)
def verify_legal_document(
    document_id: str,
    payload: DocumentVerification,
    x_admin_token: str | None = Header(default=None),
) -> dict:
    """review_required दस्तावेज़ को स्पष्ट reviewer confirmation के बाद verified करें."""
    _require_admin(x_admin_token)
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT job_id, status, canonical_url
                FROM rti.legal_documents
                WHERE id=%s
                FOR UPDATE
                """,
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="दस्तावेज़ नहीं मिला")
            job_id, current_status, canonical_url = row
            if current_status != "review_required":
                raise HTTPException(
                    status_code=409,
                    detail="केवल review_required दस्तावेज़ को verified किया जा सकता है",
                )
            cursor.execute(
                """
                UPDATE rti.legal_documents
                SET status='verified',
                    review_note=%s,
                    verified_at=now(),
                    updated_at=now(),
                    last_error_code=NULL
                WHERE id=%s
                """,
                (payload.review_note, document_id),
            )
            cursor.execute(
                """
                INSERT INTO rti.crawl_job_events(job_id,event_type,message)
                VALUES(%s,'document_verified',%s)
                """,
                (
                    job_id,
                    (
                        f"Human reviewer verified document {document_id} ({canonical_url}): "
                        f"{payload.review_note}"
                    ),
                ),
            )
        return {
            "verified": True,
            "document_id": document_id,
            "status": "verified",
            "notice": "मानव समीक्षा दर्ज हुई; दस्तावेज़ अब verified research search में उपलब्ध है।",
        }
    except HTTPException:
        raise
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Document review service is temporarily unavailable",
        ) from exc
