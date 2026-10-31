# रिपॉजिटरी पथ: rti_backend/app/api/routes/research.py
"""सत्यापित कानूनी ज्ञान-संग्रह खोज API."""

import psycopg
from fastapi import APIRouter, HTTPException

from app.models.research import LegalResearchQuery, LegalResearchResponse
from app.services.research import run_legal_research

router = APIRouter(prefix="/research", tags=["कानूनी शोध"])


@router.post("/search", response_model=LegalResearchResponse, summary="सत्यापित कानूनी स्रोत खोजें")
def search_legal_knowledge(payload: LegalResearchQuery) -> LegalResearchResponse:
    """केवल status=verified corpus लौटाएँ; crawler text को स्वतः प्रमाण न मानें."""
    try:
        return run_legal_research(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="कानूनी ज्ञान-संग्रह अभी configure नहीं है") from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="कानूनी खोज सेवा अस्थायी रूप से अनुपलब्ध है") from exc
