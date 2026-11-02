# Repository path: rti_backend/app/repositories/legal_principles.py
"""Private PostgreSQL repository for reviewed legal principle memory."""

from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.core.database import get_connection


def create_pending_principle(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT status, canonical_url FROM rti.legal_documents
               WHERE id = %s FOR SHARE""",
            (payload["document_id"],),
        )
        source = cursor.fetchone()
        if not source:
            raise LookupError("संबंधित निर्णय दस्तावेज़ नहीं मिला")
        if source[0] != "verified":
            raise PermissionError("सिद्धांत जोड़ने से पहले मूल निर्णय का document verified होना चाहिए")
        cursor.execute(
            """INSERT INTO rti.legal_principles
               (document_id, issue, principle_type, principle_text, scope,
                conditions, exceptions, applicant_arguments_accepted,
                applicant_arguments_rejected, pio_arguments_accepted,
                pio_arguments_rejected, outcome, pinpoint_citations)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING id::text, legal_status""",
            (
                UUID(payload["document_id"]), payload["issue"], payload["principle_type"],
                payload["principle_text"], payload.get("scope"),
                Jsonb(payload.get("conditions", [])), Jsonb(payload.get("exceptions", [])),
                Jsonb(payload.get("applicant_arguments_accepted", [])),
                Jsonb(payload.get("applicant_arguments_rejected", [])),
                Jsonb(payload.get("pio_arguments_accepted", [])),
                Jsonb(payload.get("pio_arguments_rejected", [])), payload.get("outcome"),
                Jsonb(payload["pinpoint_citations"]),
            ),
        )
        row = cursor.fetchone()
    return {"principle_id": row[0], "legal_status": row[1], "source_url": source[1]}


def list_pending_principles(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT p.id::text, p.document_id::text, d.title, d.canonical_url,
                      p.issue, p.principle_type, p.principle_text, p.scope,
                      p.conditions, p.exceptions, p.applicant_arguments_accepted,
                      p.applicant_arguments_rejected, p.pio_arguments_accepted,
                      p.pio_arguments_rejected, p.outcome, p.pinpoint_citations,
                      p.created_at
               FROM rti.legal_principles p
               JOIN rti.legal_documents d ON d.id = p.document_id
               WHERE p.legal_status = 'pending_review'
               ORDER BY p.created_at ASC LIMIT %s""",
            (limit,),
        )
        rows = cursor.fetchall()
    keys = (
        "principle_id", "document_id", "source_title", "source_url", "issue",
        "principle_type", "principle_text", "scope", "conditions", "exceptions",
        "applicant_arguments_accepted", "applicant_arguments_rejected",
        "pio_arguments_accepted", "pio_arguments_rejected", "outcome",
        "pinpoint_citations", "created_at",
    )
    return [dict(zip(keys, row, strict=True)) for row in rows]


def review_principle(
    principle_id: UUID, status: str, reviewer_note: str,
    reviewer: str, superseded_by_document_id: UUID | None,
    subsequent_treatment: list[str],
) -> dict[str, Any] | None:
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT legal_status FROM rti.legal_principles WHERE id = %s FOR UPDATE",
            (principle_id,),
        )
        previous = cursor.fetchone()
        if not previous:
            return None
        previous_status = previous[0]
        if superseded_by_document_id is not None:
            cursor.execute(
                "SELECT 1 FROM rti.legal_documents WHERE id = %s AND status = 'verified'",
                (superseded_by_document_id,),
            )
            if not cursor.fetchone():
                raise ValueError("बाद वाला निर्णय verified corpus में उपलब्ध नहीं है")
        cursor.execute(
            """UPDATE rti.legal_principles p
               SET legal_status = %s, reviewer_note = %s, reviewed_by = %s,
                   reviewed_at = now(), superseded_by_document_id = %s,
                   subsequent_treatment = %s, updated_at = now()
               WHERE p.id = %s AND p.legal_status IN ('pending_review','needs_subsequent_review','verified_current')
                 AND EXISTS (SELECT 1 FROM rti.legal_documents d
                             WHERE d.id = p.document_id AND d.status = 'verified')
                 AND (%s <> 'verified_current' OR jsonb_array_length(p.pinpoint_citations) > 0)
               RETURNING p.id::text, p.legal_status, p.reviewed_at""",
            (status, reviewer_note, reviewer, superseded_by_document_id,
             Jsonb(subsequent_treatment), principle_id, status),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """INSERT INTO rti.legal_principle_reviews
                   (principle_id, previous_status, new_status, reviewer,
                    reviewer_note, superseded_by_document_id)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (principle_id, previous_status, status, reviewer,
                 reviewer_note, superseded_by_document_id),
            )
    if not row:
        return None
    return {"principle_id": row[0], "legal_status": row[1], "reviewed_at": row[2]}


def search_verified_principles(query: str, limit: int = 8) -> list[dict[str, Any]]:
    cleaned = " ".join(query.split())
    if not cleaned:
        return []
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """WITH q AS (SELECT websearch_to_tsquery('simple', %s) AS tsq)
               SELECT p.id::text, p.document_id::text, d.title, d.canonical_url,
                      d.court_or_authority, d.decision_date, p.issue,
                      p.principle_type, p.principle_text, p.scope,
                      p.conditions, p.exceptions, p.applicant_arguments_accepted,
                      p.applicant_arguments_rejected, p.pio_arguments_accepted,
                      p.pio_arguments_rejected, p.outcome, p.pinpoint_citations,
                      p.legal_status, p.subsequent_treatment
               FROM rti.legal_principles p
               JOIN rti.legal_documents d ON d.id = p.document_id
               CROSS JOIN q
               WHERE p.legal_status = 'verified_current'
                 AND p.principle_type = 'ratio_decidendi'
                 AND d.status = 'verified'
                 AND to_tsvector('simple', p.issue || ' ' || p.principle_text ||
                       ' ' || COALESCE(p.scope, '') || ' ' ||
                       COALESCE(d.title, '')) @@ q.tsq
               ORDER BY ts_rank(to_tsvector('simple',
                         p.issue || ' ' || p.principle_text || ' ' ||
                         COALESCE(p.scope, '') || ' ' || COALESCE(d.title, '')),
                         q.tsq) DESC, d.decision_date DESC NULLS LAST
               LIMIT %s""",
            (cleaned, limit),
        )
        rows = cursor.fetchall()
    keys = (
        "principle_id", "document_id", "source_title", "source_url", "authority",
        "decision_date", "issue", "principle_type", "principle_text", "scope",
        "conditions", "exceptions", "applicant_arguments_accepted",
        "applicant_arguments_rejected", "pio_arguments_accepted",
        "pio_arguments_rejected", "outcome", "pinpoint_citations",
        "legal_status", "subsequent_treatment",
    )
    return [dict(zip(keys, row, strict=True)) for row in rows]
