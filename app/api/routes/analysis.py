# रिपॉजिटरी पथ: rti_backend/app/api/routes/analysis.py
"""Applicant/PIO के लिए निष्पक्ष प्रारंभिक कानूनी जाँच-सूची."""

from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.services.legal_analysis import AnalysisRole, build_analysis_instructions

router = APIRouter(prefix="/analysis", tags=["प्रारंभिक विश्लेषण"])


class AnalysisChecklistRequest(BaseModel):
    """प्रारंभिक मुद्दा-विश्लेषण के लिए role और तथ्य-सार."""

    model_config = ConfigDict(extra="forbid")

    role: AnalysisRole
    facts: str = Field(min_length=20, max_length=6000)


class AnalysisChecklistResponse(BaseModel):
    """निष्पक्ष जाँच-सूची, न कि AI-generated final legal opinion."""

    role: AnalysisRole
    facts_received: bool
    checklist: list[str]
    reasoning_guardrails: str
    notice: str


APPLICANT_CHECKLIST = [
    "माँगी गई सूचना को अलग-अलग, स्पष्ट और पहचान योग्य अभिलेख-बिंदुओं में बाँटें।",
    "आवेदन की तारीख, प्राप्ति का प्रमाण, शुल्क और संबंधित लोक प्राधिकरण जाँचें।",
    "PIO के उत्तर/अस्वीकृति में उद्धृत प्रत्येक धारा और उसके आवश्यक तत्व जाँचें।",
    "आंशिक प्रकटीकरण, अभिलेख निरीक्षण और उपलब्ध अपील/शिकायत उपायों पर विचार करें।",
    "प्रथम अपील की समय-सीमा और सक्षम प्रथम अपीलीय प्राधिकारी की पुष्टि करें।",
]
PIO_CHECKLIST = [
    "संबंधित शाखाओं और अभिलेख-धारकों में उचित रिकॉर्ड खोज का दस्तावेजीकरण करें।",
    "सूचना उपलब्ध है, अस्तित्व में नहीं है, अन्य प्राधिकरण के पास है या नष्ट हुई—स्थिति अलग करें।",
    "धारा 8/9 का कोई अपवाद लागू हो तो उसके प्रत्येक आवश्यक तत्व और वर्तमान न्यायिक व्याख्या जाँचें।",
    "धारा 10 के तहत पृथक्करण/आंशिक प्रकटीकरण की संभावना जाँचें।",
    "धारा 11 की third-party प्रक्रिया केवल जहाँ वैधानिक रूप से लागू हो वहाँ जाँचें।",
    "उत्तर, शुल्क-सूचना और कारणयुक्त आदेश की वैधानिक समय-सीमा जाँचें।",
]


@router.post("/checklist", response_model=AnalysisChecklistResponse, summary="Applicant/PIO मुद्दा-जाँच सूची")
def create_analysis_checklist(payload: AnalysisChecklistRequest) -> AnalysisChecklistResponse:
    """दिए गए तथ्य-सार के लिए role-specific checklist लौटाएँ."""
    checklist = (
        APPLICANT_CHECKLIST
        if payload.role == AnalysisRole.APPLICANT
        else PIO_CHECKLIST
    )
    return AnalysisChecklistResponse(
        role=payload.role,
        facts_received=True,
        checklist=checklist,
        reasoning_guardrails=build_analysis_instructions(payload.role),
        notice=(
            "यह नियम-आधारित प्रारंभिक checklist है। अभी कोई AI model inference, "
            "case-law matching या अंतिम कानूनी राय नहीं दी गई है; तथ्य और वर्तमान "
            "प्राथमिक स्रोतों की मानव समीक्षा आवश्यक है।"
        ),
    )
