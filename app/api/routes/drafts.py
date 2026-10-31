# रिपॉजिटरी पथ: rti_backend/app/api/routes/drafts.py
"""RTI application draft API; कोई submission या portal action नहीं."""

from fastapi import APIRouter

from app.models.drafts import FirstAppealDraftRequest, RTIDraftRequest
from app.services.drafting import build_first_appeal_draft, build_rti_draft

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


@router.post("/first-appeal", summary="प्रथम अपील का संपादन योग्य मसौदा बनाएँ")
def create_first_appeal_draft(payload: FirstAppealDraftRequest) -> dict[str, str | bool]:
    """धारा 19(1) का मसौदा लौटाएँ; अपील कहीं दाखिल नहीं होती."""
    return {
        "created": True,
        "submitted": False,
        "requires_user_review": True,
        "draft": build_first_appeal_draft(payload),
        "notice": (
            "अपील की समय-सीमा, सक्षम प्रथम अपीलीय प्राधिकारी, लागू नियम और तथ्यों "
            "की जाँच करें। यह मसौदा स्वतः दाखिल नहीं किया गया है।"
        ),
    }
