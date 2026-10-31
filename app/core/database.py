# रिपॉजिटरी पथ: rti_backend/app/core/database.py
"""PostgreSQL connections and safe health checks."""

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg

from app.core.config import settings


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """एक transaction-scoped PostgreSQL connection दें."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    with psycopg.connect(
        settings.database_url,
        connect_timeout=settings.database_connect_timeout,
        application_name="rti-intelligence-backend",
    ) as connection:
        yield connection


def database_health() -> dict[str, Any]:
    """कनेक्शन की न्यूनतम स्थिति लौटाएँ; secrets या raw errors नहीं."""
    if not settings.database_url:
        return {"status": "not_configured", "database": "postgresql"}
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"status": "connected", "database": "postgresql"}
    except (psycopg.Error, RuntimeError):
        return {"status": "unavailable", "database": "postgresql"}
