# रिपॉजिटरी पथ: rti_backend/app/repositories/legal_knowledge.py
"""Verified legal corpus के लिए parameterized PostgreSQL queries."""

from typing import Any

from app.core.database import get_connection


def search_verified_documents(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """केवल मानव-सत्यापित दस्तावेज़ों में exact phrase substring खोजें."""
    # LIKE wildcard को literal बनाएँ ताकि user input SQL pattern न बदल सके।
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id::text, title, canonical_url, court_or_authority,
                   decision_date, document_type,
                   LEFT(extracted_text, 1600), content_sha256
            FROM rti.legal_documents
            WHERE status = 'verified'
              AND extracted_text IS NOT NULL
              AND extracted_text ILIKE %s ESCAPE E'\\\\'
            ORDER BY decision_date DESC NULLS LAST, updated_at DESC
            LIMIT %s
            """,
            (pattern, limit),
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
