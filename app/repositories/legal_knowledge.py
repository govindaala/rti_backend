# रिपॉजिटरी पथ: rti_backend/app/repositories/legal_knowledge.py
"""Verified legal corpus के लिए ranked search; response में compact structured knowledge प्राथमिक है."""

from typing import Any

from app.core.database import get_connection


def search_verified_documents(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """सत्यापित दस्तावेज़ खोजें और raw full-text के बजाय structured synopsis लौटाएँ."""
    cleaned_query = " ".join(query.split())
    if not cleaned_query:
        return []

    escaped = cleaned_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            WITH search_input AS (
                SELECT websearch_to_tsquery('simple', %s) AS ts_query
            ),
            candidates AS (
                SELECT d.id::text, d.title, d.canonical_url, d.court_or_authority,
                       d.decision_date, d.document_type,
                       LEFT(COALESCE(d.learned_summary, '') || ' ' ||
                            COALESCE(d.legal_issue, '') || ' ' ||
                            COALESCE(d.holding, '') || ' ' ||
                            COALESCE(array_to_string(d.cited_sections, ', '), ''), 1600) AS excerpt,
                       d.learned_summary, d.legal_issue, d.holding,
                       COALESCE(d.cited_sections, ARRAY[]::text[]) AS cited_sections,
                       d.key_paragraphs AS decision_candidates,
                       d.content_sha256,
                       ts_rank(
                           to_tsvector('simple',
                               COALESCE(d.title, '') || ' ' ||
                               COALESCE(d.learned_summary, '') || ' ' ||
                               COALESCE(d.legal_issue, '') || ' ' ||
                               COALESCE(d.holding, '') || ' ' ||
                               COALESCE(array_to_string(d.cited_sections, ', '), '') || ' ' ||
                               COALESCE(d.extracted_text, '')),
                           search_input.ts_query
                       ) AS relevance,
                       CASE WHEN d.extracted_text ILIKE %s ESCAPE E'\\\\'
                                  OR COALESCE(d.title, '') ILIKE %s ESCAPE E'\\\\'
                                  OR COALESCE(d.learned_summary, '') ILIKE %s ESCAPE E'\\\\'
                                  OR COALESCE(d.legal_issue, '') ILIKE %s ESCAPE E'\\\\'
                                  OR COALESCE(d.holding, '') ILIKE %s ESCAPE E'\\\\'
                            THEN 1 ELSE 0 END AS substring_match
                FROM rti.legal_documents AS d
                CROSS JOIN search_input
                WHERE d.status = 'verified'
                  AND d.extracted_text IS NOT NULL
                  AND (
                    to_tsvector('simple',
                        COALESCE(d.title, '') || ' ' ||
                        COALESCE(d.learned_summary, '') || ' ' ||
                        COALESCE(d.legal_issue, '') || ' ' ||
                        COALESCE(d.holding, '') || ' ' ||
                        COALESCE(array_to_string(d.cited_sections, ', '), '') || ' ' ||
                        COALESCE(d.extracted_text, '')) @@ search_input.ts_query
                    OR d.extracted_text ILIKE %s ESCAPE E'\\\\'
                    OR COALESCE(d.title, '') ILIKE %s ESCAPE E'\\\\'
                    OR COALESCE(d.learned_summary, '') ILIKE %s ESCAPE E'\\\\'
                    OR COALESCE(d.legal_issue, '') ILIKE %s ESCAPE E'\\\\'
                    OR COALESCE(d.holding, '') ILIKE %s ESCAPE E'\\\\'
                  )
            )
            SELECT id, title, canonical_url, court_or_authority,
                   decision_date, document_type, excerpt, content_sha256,
                   learned_summary, legal_issue, holding, cited_sections, decision_candidates
            FROM candidates
            ORDER BY relevance DESC, substring_match DESC,
                     decision_date DESC NULLS LAST, canonical_url ASC
            LIMIT %s
            """,
            (cleaned_query, pattern, pattern, pattern, pattern, pattern,
             pattern, pattern, pattern, pattern, pattern, limit),
        )
        rows = cursor.fetchall()

    return [
        {
            "document_id": row[0], "title": row[1] or row[2],
            "canonical_url": row[2], "authority": row[3],
            "decision_date": row[4], "document_type": row[5],
            "excerpt": row[6] or "", "content_sha256": row[7],
            "learned_summary": row[8], "legal_issue": row[9],
            "holding": row[10], "cited_sections": row[11] or [],
            "decision_candidates": row[12] or [],
            "verification_status": "verified",
        }
        for row in rows
    ]



def search_candidate_documents(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve machine-extracted candidates without promoting them to verified evidence."""
    cleaned_query = " ".join(query.split())
    if not cleaned_query:
        return []

    escaped = cleaned_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            WITH search_input AS (
                SELECT websearch_to_tsquery('simple', %s) AS ts_query
            ),
            candidates AS (
                SELECT d.id::text, d.title, d.canonical_url, d.court_or_authority,
                       d.decision_date, d.document_type,
                       LEFT(COALESCE(d.learned_summary, '') || ' ' ||
                            COALESCE(d.legal_issue, '') || ' ' ||
                            COALESCE(d.holding, '') || ' ' ||
                            COALESCE(array_to_string(d.cited_sections, ', '), '') || ' ' ||
                            COALESCE(d.extracted_text, ''), 1600) AS excerpt,
                       d.content_sha256, d.learned_summary, d.legal_issue, d.holding,
                       COALESCE(d.cited_sections, ARRAY[]::text[]) AS cited_sections,
                       d.key_paragraphs AS decision_candidates,
                       d.analysis_status, d.analysis_method, d.extraction_status,
                       ts_rank(
                           to_tsvector('simple',
                               COALESCE(d.title, '') || ' ' ||
                               COALESCE(d.learned_summary, '') || ' ' ||
                               COALESCE(d.legal_issue, '') || ' ' ||
                               COALESCE(d.holding, '') || ' ' ||
                               COALESCE(array_to_string(d.cited_sections, ', '), '') || ' ' ||
                               COALESCE(d.extracted_text, '')),
                           search_input.ts_query
                       ) AS relevance
                FROM rti.legal_documents AS d
                CROSS JOIN search_input
                WHERE d.status = 'review_required'
                  AND d.analysis_status = 'human_review_required'
                  AND d.extracted_text IS NOT NULL
                  AND length(trim(d.extracted_text)) > 0
                  AND (
                    to_tsvector('simple',
                        COALESCE(d.title, '') || ' ' ||
                        COALESCE(d.learned_summary, '') || ' ' ||
                        COALESCE(d.legal_issue, '') || ' ' ||
                        COALESCE(d.holding, '') || ' ' ||
                        COALESCE(array_to_string(d.cited_sections, ', '), '') || ' ' ||
                        COALESCE(d.extracted_text, '')) @@ search_input.ts_query
                    OR d.extracted_text ILIKE %s
                  )
            )
            SELECT id, title, canonical_url, court_or_authority,
                   decision_date, document_type, excerpt, content_sha256,
                   learned_summary, legal_issue, holding, cited_sections,
                   decision_candidates, analysis_status, analysis_method, extraction_status
            FROM candidates
            ORDER BY relevance DESC, decision_date DESC NULLS LAST, canonical_url ASC
            LIMIT %s
            """,
            (cleaned_query, pattern, limit),
        )
        rows = cursor.fetchall()

    return [
        {
            "document_id": row[0], "title": row[1] or row[2],
            "canonical_url": row[2], "authority": row[3],
            "decision_date": row[4], "document_type": row[5] or "unknown",
            "excerpt": row[6] or "", "content_sha256": row[7],
            "learned_summary": row[8], "legal_issue": row[9],
            "holding": row[10], "cited_sections": row[11] or [],
            "decision_candidates": row[12] or [],
            "analysis_status": row[13], "analysis_method": row[14],
            "extraction_status": row[15],
            "verification_status": "machine_extracted_candidate",
        }
        for row in rows
    ]
