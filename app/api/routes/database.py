# रिपॉजिटरी पथ: rti_backend/app/api/routes/database.py
"""Database readiness endpoint."""

from fastapi import APIRouter

from app.core.database import database_health

router = APIRouter(prefix="/health", tags=["स्वास्थ्य"])


@router.get("/database", summary="PostgreSQL कनेक्शन की स्थिति")
def database_readiness() -> dict[str, str]:
    """Return a safe, non-sensitive database connectivity status."""
    return database_health()
