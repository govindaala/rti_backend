# रिपॉजिटरी पथ: rti_backend/app/repositories/legal_knowledge.py
"""Verified legal corpus के लिए ranked PostgreSQL full-text search."""

from typing import Any

from app.core.database import get_connection


def search_verified_documents(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """सत्यापित दस्तावेज़ों को relevance के अनुसार खोजें; substring fallback भी रखें."""
    cleaned_query = " ".join(query.split())
    if not cleaned_query:
        return []

    # Search terms को PostgreSQL web-search parser संभालता है; SQL values parameterized हैं।
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
                       LEFT(d.extracted_text, 1600) AS excerpt, d.content_sha256,
                       ts_rank(
                           to_tsvector(
                               'simple',
                               COALESCE(d.title, '') || ' ' || COALESCE(d.extracted_text, '')
                           ),
                           search_input.ts_query
                       ) AS relevance,
                       CASE WHEN d.extracted_text ILIKE %s ESCAPE E'\\\\'
                                  OR COALESCE(d.title, '') ILIKE %s ESCAPE E'\\\\'
                            THEN 1 ELSE 0 END AS substring_match
                FROM rti.legal_documents AS d
                CROSS JOIN search_input
                WHERE d.status = 'verified'
                  AND d.extracted_text IS NOT NULL
                  AND (
                    to_tsvector(
                        'simple',
                        COALESCE(d.title, '') || ' ' || COALESCE(d.extracted_text, '')
                    ) @@ search_input.ts_query
                    OR d.extracted_text ILIKE %s ESCAPE E'\\\\'
                    OR COALESCE(d.title, '') ILIKE %s ESCAPE E'\\\\'
                  )
            )
            SELECT id, title, canonical_url, court_or_authority,
                   decision_date, document_type, excerpt, content_sha256
            FROM candidates
            ORDER BY relevance DESC, substring_match DESC,
                     decision_date DESC NULLS LAST, canonical_url ASC
            LIMIT %s
            """,
            (cleaned_query, pattern, pattern, pattern, pattern, limit),
        )
        rows = cursor.fetchall()

    return [
        {
            "document_id": row[0],
            "title": row[1] or row[2],
            "canonical_url": row[2],
            "authority": row[3],
            "decision_date": row[4],
            "document_type": row[5],
            "excerpt": row[6] or "",
            "content_sha256": row[7],
        }
        for row in rows
    ]
