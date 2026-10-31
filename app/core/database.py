# रिपॉजिटरी पथ: rti_backend/app/core/database.py
"""PostgreSQL connectivity checks without exposing credentials or server errors."""

from typing import Any

import psycopg

from app.core.config import settings


def database_health() -> dict[str, Any]:
    """Return a minimal database status; never return the connection string."""
    if not settings.database_url:
        return {"status": "not_configured", "database": "postgresql"}

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.database_connect_timeout,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return {"status": "connected", "database": "postgresql"}
    except psycopg.Error:
        # Do not leak hostnames, usernames, passwords, or provider error details.
        return {"status": "unavailable", "database": "postgresql"}
