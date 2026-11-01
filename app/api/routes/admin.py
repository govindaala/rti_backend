# रिपॉजिटरी पथ: rti_backend/app/api/routes/admin.py
"""Session-authenticated live operations dashboard and privileged admin APIs."""

import hmac
import logging
from urllib.parse import urlsplit

import psycopg
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.core.admin_auth import COOKIE_NAME, SESSION_TTL_SECONDS, create_session, require_admin
from app.core.config import settings
from app.core.database import get_connection
from app.services.source_registry import is_official_source_url
from app.services.default_catalog import DEFAULT_SOURCE_CATALOG, RELATED_LAW_DISCOVERY
from app.worker import process_one

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
                """SELECT
                    count(*) FILTER (WHERE created_at >= (date_trunc('day', now() AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata')),
                    count(*) FILTER (WHERE read_at >= (date_trunc('day', now() AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata')),
                    count(*) FILTER (WHERE analyzed_at >= (date_trunc('day', now() AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata')),
                    count(*) FILTER (WHERE analysis_status = 'human_review_required')
                   FROM rti.legal_documents"""
            )
            daily_documents_found, daily_documents_read, daily_preliminary_analyses, awaiting_human_review = cursor.fetchone()
            cursor.execute(
                """SELECT count(*) FROM rti.crawl_jobs
                   WHERE status = 'failed'
                     AND updated_at >= (date_trunc('day', now() AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata')"""
            )
            daily_failed_jobs = cursor.fetchone()[0]
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
                          status, created_at, ocr_required, extraction_status,
                          decision_date, court_name, case_number, read_at, analysis_status,
                          learned_summary, legal_issue, holding, cited_sections,
                          key_paragraphs, analysis_method, analyzed_at
                   FROM rti.legal_documents ORDER BY created_at DESC LIMIT 25"""
            )
            recent_documents = [
                {"id": r[0], "job_id": r[1], "title": r[2], "url": r[3],
                 "type": r[4], "status": r[5], "created_at": r[6].isoformat(),
                 "ocr_required": r[7], "extraction_status": r[8],
                 "decision_date": r[9].isoformat() if r[9] else None,
                 "court_name": r[10], "case_number": r[11],
                 "read_at": r[12].isoformat() if r[12] else None,
                 "analysis_status": r[13], "learned_summary": r[14],
                 "legal_issue": r[15], "holding": r[16], "cited_sections": r[17],
                 "key_paragraphs": r[18], "analysis_method": r[19],
                 "analyzed_at": r[20].isoformat() if r[20] else None}
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
                            "daily_documents_found": daily_documents_found,
                            "daily_documents_read": daily_documents_read,
                            "daily_preliminary_analyses": daily_preliminary_analyses,
                            "daily_failed_jobs": daily_failed_jobs,
                            "awaiting_human_review": awaiting_human_review,
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


@router.get("/admin/documents/ocr-pending", summary="OCR pending दस्तावेज़ों की paginated सूची")
def list_ocr_pending_documents(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
) -> dict:
    """केवल OCR-pending दस्तावेज़ दिखाएँ; कानूनी verification status न बदलें."""
    require_admin(request)
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="Database is not configured")
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT id::text, title, canonical_url, extraction_status, updated_at
                   FROM rti.legal_documents
                   WHERE ocr_required = true AND status = 'needs_ocr'
                   ORDER BY updated_at DESC, id
                   LIMIT %s OFFSET %s""",
                (limit + 1, offset),
            )
            rows = cursor.fetchall()
        has_more = len(rows) > limit
        items = [
            {
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "extraction_status": row[3],
                "updated_at": row[4].isoformat(),
                "ocr_required": True,
                "status": "needs_ocr",
            }
            for row in rows[:limit]
        ]
        return {"items": items, "limit": limit, "offset": offset, "has_more": has_more}
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="OCR backlog is temporarily unavailable") from exc


@router.post(
    "/admin/documents/{document_id}/retry-ocr",
    status_code=202,
    summary="OCR pending दस्तावेज़ को दोबारा queue करें",
)
def retry_ocr_document(
    document_id: str,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """केवल OCR-pending दस्तावेज़ को फिर से crawl/OCR queue में डालें; verify कभी न करें."""
    require_admin(request, x_csrf_token)
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT d.source_id, d.canonical_url, d.status, d.ocr_required, s.status
                   FROM rti.legal_documents AS d
                   JOIN rti.research_sources AS s ON s.id = d.source_id
                   WHERE d.id = %s
                   FOR UPDATE OF d, s""",
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="दस्तावेज़ नहीं मिला")
            source_id, canonical_url, document_status, ocr_required, source_status = row
            if document_status != "needs_ocr" or not ocr_required:
                raise HTTPException(
                    status_code=409,
                    detail="केवल needs_ocr स्थिति वाला दस्तावेज़ दोबारा OCR queue में जा सकता है",
                )
            if source_status == "paused":
                raise HTTPException(
                    status_code=409,
                    detail="स्रोत paused है; पहले source को resume करें",
                )
            cursor.execute(
                """INSERT INTO rti.crawl_jobs (source_id, status, current_url)
                   SELECT %s, 'queued', %s
                   WHERE NOT EXISTS (
                       SELECT 1 FROM rti.crawl_jobs
                       WHERE source_id = %s AND current_url = %s
                         AND status IN ('queued', 'running')
                   )
                   RETURNING id::text""",
                (source_id, canonical_url, source_id, canonical_url),
            )
            job = cursor.fetchone()
            if not job:
                cursor.execute(
                    """SELECT id::text FROM rti.crawl_jobs
                       WHERE source_id = %s AND current_url = %s
                         AND status IN ('queued', 'running')
                       ORDER BY created_at DESC LIMIT 1""",
                    (source_id, canonical_url),
                )
                existing = cursor.fetchone()
                if not existing:
                    raise HTTPException(
                        status_code=503,
                        detail="OCR retry job enqueue नहीं हो सका; कृपया फिर प्रयास करें",
                    )
                return {
                    "accepted": True,
                    "queued": False,
                    "document_id": document_id,
                    "job_id": existing[0],
                    "message": "इस दस्तावेज़ का crawl पहले से queued या running है",
                }
            job_id = job[0]
            cursor.execute(
                """UPDATE rti.research_sources
                   SET status = 'discovering', last_error_code = NULL, updated_at = now()
                   WHERE id = %s""",
                (source_id,),
            )
            cursor.execute(
                """INSERT INTO rti.crawl_job_events (job_id, event_type, message)
                   VALUES (%s, 'ocr_retry_queued', %s)""",
                (job_id, f"Administrator requested OCR retry for document {document_id}"),
            )
        return {
            "accepted": True,
            "queued": True,
            "document_id": document_id,
            "job_id": job_id,
            "message": "दस्तावेज़ दोबारा fetch और OCR के लिए queue हुआ; human verification आवश्यक रहेगी",
        }
    except HTTPException:
        raise
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="OCR retry queue service is unavailable") from exc


@router.get("/admin/queue-health", summary="Background worker queue health")
def queue_health(request: Request) -> dict:
    """Queue backlog और stale running jobs दिखाएँ; process alive होने का झूठा दावा न करें."""
    require_admin(request)
    if not settings.database_url:
        return {
            "database": "not_configured",
            "queue_health": "unknown",
            "queued_ready": 0,
            "queued_delayed": 0,
            "running": 0,
            "stale_running": 0,
            "failed": 0,
            "oldest_ready_age_seconds": None,
            "latest_job_heartbeat_at": None,
            "last_completed_at": None,
            "worker_status": "unknown",
            "online_workers": 0,
            "stale_workers": 0,
            "latest_worker_seen_at": None,
            "worker_stale_after_seconds": 60,
            "stale_after_seconds": 600,
        }
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                     count(*) FILTER (
                       WHERE status = 'queued' AND available_at <= now()
                     ),
                     count(*) FILTER (
                       WHERE status = 'queued' AND available_at > now()
                     ),
                     count(*) FILTER (WHERE status = 'running'),
                     count(*) FILTER (
                       WHERE status = 'running'
                         AND COALESCE(heartbeat_at, started_at, updated_at)
                             < now() - interval '10 minutes'
                     ),
                     count(*) FILTER (WHERE status = 'failed'),
                     floor(extract(epoch FROM (
                       now() - min(created_at) FILTER (
                         WHERE status = 'queued' AND available_at <= now()
                       )
                     )))::bigint,
                     max(heartbeat_at) FILTER (WHERE status = 'running'),
                     max(finished_at) FILTER (WHERE status = 'completed'),
                     (SELECT count(*) FROM rti.worker_heartbeats
                      WHERE status = 'running'
                        AND last_seen_at >= now() - interval '60 seconds'),
                     (SELECT count(*) FROM rti.worker_heartbeats
                      WHERE status = 'running'
                        AND last_seen_at < now() - interval '60 seconds'),
                     (SELECT max(last_seen_at) FROM rti.worker_heartbeats)
                   FROM rti.crawl_jobs"""
            )
            row = cursor.fetchone()
        if not row:
            raise RuntimeError("Queue health query returned no result")
        (
            queued_ready, queued_delayed, running, stale_running, failed, oldest_age,
            heartbeat, completed, online_workers, stale_workers, worker_seen,
        ) = row
        queued_ready = int(queued_ready or 0)
        queued_delayed = int(queued_delayed or 0)
        running = int(running or 0)
        stale_running = int(stale_running or 0)
        failed = int(failed or 0)
        online_workers = int(online_workers or 0)
        stale_workers = int(stale_workers or 0)
        worker_status = "online" if online_workers else ("stale" if stale_workers else "offline")
        if (
            stale_running
            or (queued_ready and oldest_age is not None and oldest_age >= 600)
            or (queued_ready and worker_status != "online")
        ):
            health = "attention"
        elif queued_ready or running or queued_delayed:
            health = "busy"
        else:
            health = "idle"
        return {
            "database": "connected",
            "queue_health": health,
            "queued_ready": queued_ready,
            "queued_delayed": queued_delayed,
            "running": running,
            "stale_running": stale_running,
            "failed": failed,
            "oldest_ready_age_seconds": int(oldest_age) if oldest_age is not None else None,
            "latest_job_heartbeat_at": heartbeat.isoformat() if heartbeat else None,
            "last_completed_at": completed.isoformat() if completed else None,
            "worker_status": worker_status,
            "online_workers": online_workers,
            "stale_workers": stale_workers,
            "latest_worker_seen_at": worker_seen.isoformat() if worker_seen else None,
            "worker_stale_after_seconds": 60,
            "stale_after_seconds": 600,
        }
    except (psycopg.Error, RuntimeError):
        logger.exception("Queue health query failed")
        raise HTTPException(status_code=503, detail="Queue health is temporarily unavailable") from None



@router.post("/scheduler/official-discovery", summary="Scheduled official-court decision discovery")
def scheduled_official_discovery(authorization: str | None = Header(default=None)) -> dict:
    """Run a bounded official-source batch; token must live in hosting secrets."""
    expected = settings.scheduler_token or ""
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not expected or not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid scheduler credential")
    source_ids: list[str] = []
    new_jobs = 0
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
                       ON CONFLICT (normalized_url) DO NOTHING""",
                    (url, url, item["name"]),
                )
                cursor.execute("SELECT id FROM rti.research_sources WHERE normalized_url=%s", (url,))
                row = cursor.fetchone()
                if not row:
                    continue
                source_id = row[0]
                source_ids.append(source_id)
                cursor.execute(
                    """INSERT INTO rti.crawl_jobs (source_id, status, current_url)
                       SELECT %s, 'queued', %s
                       WHERE NOT EXISTS (
                         SELECT 1 FROM rti.crawl_jobs
                         WHERE source_id=%s AND current_url=%s
                           AND (status IN ('queued','running')
                                OR (status='completed' AND created_at >= now() - interval '20 hours'))
                       )
                       RETURNING id""",
                    (source_id, url, source_id, url),
                )
                job = cursor.fetchone()
                if job:
                    new_jobs += 1
                    cursor.execute(
                        """INSERT INTO rti.crawl_job_events(job_id,event_type,message)
                           VALUES(%s,'scheduled','Daily official-source scan queued')""",
                        (job[0],),
                    )
        limit = max(1, min(settings.scheduler_max_jobs_per_run, 20))
        processed = 0
        for _ in range(limit):
            if not process_one(allowed_source_ids=source_ids):
                break
            processed += 1
        return {"ok": True, "official_sources": len(source_ids), "new_jobs": new_jobs,
                "processed_jobs": processed, "job_limit": limit,
                "preliminary_analysis": "local extractive; human review required",
                "ai_analysis": "not configured; no external provider called"}
    except (psycopg.Error, RuntimeError) as exc:
        logger.exception("Scheduled official discovery failed")
        raise HTTPException(status_code=503, detail="Official discovery batch failed") from exc
