# रिपॉजिटरी पथ: rti_backend/app/api/routes/drafts.py
"""RTI application draft API; कोई submission या portal action नहीं."""

from fastapi import APIRouter

from app.models.drafts import RTIDraftRequest
from app.services.drafting import build_rti_draft

router = APIRouter(prefix="/drafts", tags=["ड्राफ्ट"])


@router.post("/rti", summary="RTI आवेदन का संपादन योग्य मसौदा बनाएँ")
def create_rti_draft(payload: RTIDraftRequest) -> dict[str, str | bool]:
    """केवल text draft लौटाएँ; कोई डेटा database में save या submit नहीं होता."""
    return {
        "created": True,
        "submitted": False,
        "requires_user_review": True,
        "draft": build_rti_draft(payload),
        "notice": (
            "राज्य/केंद्र के लागू RTI Rules, शुल्क, BPL छूट, सही लोक प्राधिकरण और "
            "पते की जाँच करके स्वयं संपादित करें। यह मसौदा स्वतः दाखिल नहीं किया गया है।"
        ),
    }
