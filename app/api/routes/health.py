# रिपॉजिटरी पथ: rti_backend/app/api/routes/health.py
"""सेवा की उपलब्धता जाँचने वाला endpoint."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["स्वास्थ्य जाँच"])


@router.get("/health", summary="API की स्वास्थ्य स्थिति")
def health_check() -> dict[str, str]:
    """बिना संवेदनशील जानकारी उजागर किए सेवा की स्थिति लौटाएँ."""
    return {
        "status": "ok",
        "service": settings.app_name,
    }
