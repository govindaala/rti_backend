# रिपॉजिटरी पथ: rti_backend/app/main.py
"""RTI Backend का FastAPI प्रवेश बिंदु."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
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


@app.get("/", tags=["मूल"], summary="API परिचय")
def root() -> dict[str, str]:
    """API का संक्षिप्त परिचय और health endpoint का रास्ता दें."""
    return {
        "message": "RTI Intelligence Platform Backend",
        "health_endpoint": f"{settings.api_v1_prefix}/health",
        "docs_endpoint": "/docs",
    }
