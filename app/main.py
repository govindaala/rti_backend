# रिपॉजिटरी पथ: rti_backend/app/main.py
"""RTI Backend का FastAPI प्रवेश बिंदु."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.database import router as database_router
from app.api.routes.health import router as health_router
from app.api.routes.legal_cases import router as legal_cases_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "RTI कानूनी शोध और विश्लेषण के लिए बैकएंड API। "
        "यह सेवा स्वयं RTI आवेदन या अपील दाखिल नहीं करती।"
    ),
)

# सभी संस्करणित API endpoints को एक साझा prefix के अंतर्गत रखें।
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(database_router, prefix=settings.api_v1_prefix)
app.include_router(legal_cases_router, prefix=settings.api_v1_prefix)

# वेब UI को इसी रिपॉजिटरी से serve करें; कोई अलग frontend service आवश्यक नहीं।
WEB_DIRECTORY = Path(__file__).resolve().parent.parent / "web"
app.mount("/assets", StaticFiles(directory=WEB_DIRECTORY), name="assets")


@app.get("/app", include_in_schema=False)
def user_interface() -> FileResponse:
    """नागरिक/आवेदक के लिए बहुभाषी UI लौटाएँ."""
    return FileResponse(WEB_DIRECTORY / "index.html")


@app.get("/admin", include_in_schema=False)
def admin_interface() -> FileResponse:
    """केंद्रीय Admin Panel का प्रारंभिक UI लौटाएँ."""
    return FileResponse(WEB_DIRECTORY / "admin.html")


@app.get("/", tags=["मूल"], summary="API परिचय")
def root() -> dict[str, str]:
    """API का संक्षिप्त परिचय और health endpoint का रास्ता दें."""
    return {
        "message": "RTI Intelligence Platform Backend",
        "health_endpoint": f"{settings.api_v1_prefix}/health",
        "database_health_endpoint": f"{settings.api_v1_prefix}/health/database",
        "docs_endpoint": "/docs",
    }
