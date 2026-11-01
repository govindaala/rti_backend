"""Session-authenticated live operations dashboard and privileged admin APIs."""

import hmac
import logging
from urllib.parse import urlsplit

import psycopg
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.core.admin_auth import COOKIE_NAME, SESSION_TTL_SECONDS, create_session, require_admin
from app.core.config import settings
from app.core.database import get_connection
from app.services.source_registry import is_official_source_url
from app.services.default_catalog import DEFAULT_SOURCE_CATALOG, RELATED_LAW_DISCOVERY

router = APIRouter(tags=["प्रशासन"])
logger = logging.getLogger("rti.admin_auth")


class AdminLogin(BaseModel):
    """Admin sign-in credentials; never logged or returned."""

    admin_id: str = Field(min_length=1, max_length=200)
    admin_pass: str = Field(min_length=1, max_length=500)


class DocumentVerification(BaseModel):
    """मानव reviewer द्वारा कानूनी दस्तावेज़ सत्यापन की पुष्टि."""

    review_note: str = Field(min_length=20, max_length=1200)
    confirm_reviewed: bool

    @model_validator(mode="after")
    def require_explicit_confirmation(self) -> "DocumentVerification":
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


@router.post("/admin/auth/login", summary="Administrator login")
def admin_login(payload: AdminLogin, response: Response) -> dict[str, str]:
    """Render environment credentials से signed HttpOnly session बनाएँ."""
    expected_id = settings.admin_id or ""
    expected_pass = settings.admin_pass or ""
    id_ok = hmac.compare_digest(payload.admin_id.encode(), expected_id.encode())
    pass_ok = hmac.compare_digest(payload.admin_pass.encode(), expected_pass.encode())
    if not expected_id or not expected_pass or not id_ok or not pass_ok:
        # केवल lengths और configured flags लॉग हों; credentials कभी नहीं।
        logger.warning(
            "Admin login rejected: configured ADMIN_ID=%s (%d bytes), "
            "ADMIN_PASS=%s (%d bytes); submitted ID=%d bytes, password=%d bytes",
            bool(expected_id),
            len(expected_id.encode("utf-8")),
            bool(expected_pass),
            len(expected_pass.encode("utf-8")),
            len(payload.admin_id.encode("utf-8")),
            len(payload.admin_pass.encode("utf-8")),
        )
        raise HTTPException(status_code=401, detail="गलत Admin ID या Password")
    token, csrf = create_session()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"authenticated": "true", "csrf_token": csrf, "expires_in": str(SESSION_TTL_SECONDS)}


@router.get("/admin/auth/me", summary="Current administrator session")
def admin_me(request: Request) -> dict[str, str]:
    session = require_admin(request)
    return {"authenticated": "true", "csrf_token": session["csrf"], "admin_id": session["sub"]}


@router.post("/admin/auth/logout", summary="Administrator logout")
def admin_logout(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
) -> dict[str, bool]:
    require_admin(request, x_csrf_token)
    response.delete_cookie(key=COOKIE_NAME, path="/", secure=True, httponly=True, samesite="strict")
    return {"logged_out": True}


@router.get("/admin/dashboard", summary="Live crawler dashboard आँकड़े")
def dashboard_summary(request: Request) -> dict:
    """केवल authenticated admin को live database operations आँकड़े दें."""
    require_admin(request)
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
                """SELECT count(*) FILTER (WHERE extracted_text IS NOT NULL AND length(trim(extracted_text)) > 0),
                          count(*) FILTER (WHERE document_type IN ('judgment','order')),
                          COALESCE(sum(octet_length(COALESCE(extracted_text, ''))), 0)
                   FROM rti.legal_documents"""
            )
            read_documents, decision_documents, extracted_bytes = cursor.fetchone()
            cursor.execute(
                """SELECT count(*) FILTER (WHERE ocr_required = true AND status = 'needs_ocr'),
                          count(*) FILTER (WHERE extraction_status = 'extracted_ocr'),
                          count(*) FILTER (WHERE extraction_status = 'empty_text')
                   FROM rti.legal_documents"""
            )
            ocr_pending, ocr_extracted, empty_text_documents = cursor.fetchone()
            cursor.execute(
                """SELECT j.id::text, j.status, j.current_url, j.discovered_count,
                          j.processed_count, j.failed_count, j.updated_at
                   FROM rti.crawl_jobs j ORDER BY j.updated_at DESC LIMIT 10"""
            )
            recent_jobs = [
                {"id": r[0], "status": r[1], "url": r[2], "discovered": r[3],
                 "processed": r[4], "failed": r[5], "updated_at": r[6].isoformat()}
                for r in cursor.fetchall()
            ]
            cursor.execute(
                """SELECT id::text, job_id::text, title, canonical_url, document_type,
                          status, created_at
                   FROM rti.legal_documents ORDER BY created_at DESC LIMIT 10"""
            )
            recent_documents = [
                {"id": r[0], "job_id": r[1], "title": r[2], "url": r[3],
                 "type": r[4], "status": r[5], "created_at": r[6].isoformat()}
                for r in cursor.fetchall()
            ]
        return {"database": "connected", "sources": sources, "jobs": jobs,
                "documents": documents, "recent_jobs": recent_jobs,
                "recent_documents": recent_documents,
                "metrics": {"read_documents": read_documents,
                            "decision_documents": decision_documents,
                            "extracted_text_bytes": extracted_bytes,
                            "ocr_pending_documents": ocr_pending,
                            "ocr_extracted_documents": ocr_extracted,
                            "empty_text_documents": empty_text_documents,
                            "default_catalog_entries": len(DEFAULT_SOURCE_CATALOG),
                            "related_law_entries": len(RELATED_LAW_DISCOVERY)}}
    except (psycopg.Error, RuntimeError):
        return {"database": "unavailable", "sources": {}, "jobs": {},
                "documents": {}, "recent_jobs": [], "recent_documents": []}



@router.post("/admin/sources/seed-defaults", summary="डिफॉल्ट आधिकारिक स्रोत queue में जोड़ें")
def seed_default_sources(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """Authenticated admin action: idempotently enqueue official catalogue entry points."""
    require_admin(request, x_csrf_token)
    added = 0
    already_present = 0
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            for item in DEFAULT_SOURCE_CATALOG:
                url = item["url"]
                if not is_official_source_url(url):
                    continue
                cursor.execute(
                    """INSERT INTO rti.research_sources
                           (submitted_url, normalized_url, source_label, status)
                       VALUES (%s, %s, %s, 'queued')
                       ON CONFLICT (normalized_url) DO NOTHING
                       RETURNING id""",
                    (url, url, item["name"]),
                )
                row = cursor.fetchone()
                if not row:
                    already_present += 1
                    cursor.execute("SELECT id FROM rti.research_sources WHERE normalized_url=%s", (url,))
                    row = cursor.fetchone()
                    if not row:
                        continue
                source_id = row[0]
                cursor.execute(
                    """INSERT INTO rti.crawl_jobs (source_id, status, current_url)
                       SELECT %s, 'queued', %s
                       WHERE NOT EXISTS (
                         SELECT 1 FROM rti.crawl_jobs
                         WHERE source_id=%s AND current_url=%s AND status IN ('queued','running')
                       ) RETURNING id""",
                    (source_id, url, source_id, url),
                )
                job = cursor.fetchone()
                if job:
                    added += 1
                    cursor.execute(
                        """INSERT INTO rti.crawl_job_events(job_id,event_type,message)
                           VALUES(%s,'queued','Default official catalogue source queued')""",
                        (job[0],),
                    )
        return {"accepted": True, "queued_jobs_added": added,
                "sources_already_present": already_present,
                "catalogue_sources": len(DEFAULT_SOURCE_CATALOG),
                "message": "Default catalogue queue operation completed"}
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Source queue is temporarily unavailable") from exc


@router.post("/admin/sources", status_code=202, summary="कानूनी स्रोत जोड़ें और crawl queue करें")
def submit_source(
    payload: SourceSubmission,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """Allowlisted HTTPS सरकारी स्रोत को durable database queue में जोड़ें."""
    require_admin(request, x_csrf_token)
    submitted_url = str(payload.url)
    parsed = urlsplit(submitted_url)
    if not is_official_source_url(submitted_url):
        raise HTTPException(status_code=422, detail="केवल allowlisted HTTPS सरकारी स्रोत स्वीकार हैं")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise HTTPException(status_code=422, detail="URL में credentials या non-standard port स्वीकार नहीं")
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO rti.research_sources
                       (submitted_url, normalized_url, source_label, status)
                   VALUES (%s, %s, %s, 'queued')
                   ON CONFLICT (normalized_url) DO UPDATE
                     SET source_label = COALESCE(EXCLUDED.source_label, rti.research_sources.source_label),
                         status = CASE WHEN rti.research_sources.status = 'paused'
                                       THEN 'queued' ELSE rti.research_sources.status END,
                         updated_at = CASE WHEN rti.research_sources.status = 'paused'
                                           THEN now() ELSE rti.research_sources.updated_at END
                   RETURNING id, status""",
                (submitted_url, submitted_url, payload.label),
            )
            source_id, source_status = cursor.fetchone()
            cursor.execute(
                """INSERT INTO rti.crawl_jobs (source_id, status, current_url)
                   SELECT %s, 'queued', %s
                   WHERE NOT EXISTS (
                     SELECT 1 FROM rti.crawl_jobs
                     WHERE source_id=%s AND current_url=%s AND status IN ('queued','running')
                   ) RETURNING id""",
                (source_id, submitted_url, source_id, submitted_url),
            )
            row = cursor.fetchone()
            if row:
                job_id, queued = row[0], True
                cursor.execute(
                    """INSERT INTO rti.crawl_job_events (job_id, event_type, message)
                       VALUES (%s, 'queued', 'Administrator approved source for crawling')""",
                    (job_id,),
                )
            else:
                cursor.execute(
                    """SELECT id FROM rti.crawl_jobs
                       WHERE source_id=%s AND current_url=%s AND status IN ('queued','running')
                       ORDER BY created_at DESC LIMIT 1""",
                    (source_id, submitted_url),
                )
                job_id, queued = cursor.fetchone()[0], False
        return {"accepted": True, "queued": queued, "source_id": str(source_id),
                "job_id": str(job_id), "source_status": source_status,
                "message": "Source queued" if queued else "Source already queued or running"}
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Source queue is temporarily unavailable") from exc


@router.post("/admin/documents/{document_id}/verify", summary="मानव समीक्षा के बाद कानूनी दस्तावेज़ verified करें")
def verify_legal_document(
    document_id: str,
    payload: DocumentVerification,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """review_required दस्तावेज़ को स्पष्ट reviewer confirmation के बाद verified करें."""
    require_admin(request, x_csrf_token)
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT job_id, status, canonical_url FROM rti.legal_documents
                   WHERE id=%s FOR UPDATE""",
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="दस्तावेज़ नहीं मिला")
            job_id, current_status, canonical_url = row
            if current_status != "review_required":
                raise HTTPException(status_code=409, detail="केवल review_required दस्तावेज़ को verified किया जा सकता है")
            cursor.execute(
                """UPDATE rti.legal_documents
                   SET status='verified', review_note=%s, verified_at=now(),
                       updated_at=now(), last_error_code=NULL WHERE id=%s""",
                (payload.review_note, document_id),
            )
            cursor.execute(
                """INSERT INTO rti.crawl_job_events(job_id,event_type,message)
                   VALUES(%s,'document_verified',%s)""",
                (job_id, f"Human reviewer verified document {document_id} ({canonical_url}): {payload.review_note}"),
            )
        return {"verified": True, "document_id": document_id, "status": "verified",
                "notice": "मानव समीक्षा दर्ज हुई; दस्तावेज़ verified research search में उपलब्ध है।"}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Document review service is temporarily unavailable") from exc
