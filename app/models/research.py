# रिपॉजिटरी पथ: rti_backend/app/models/research.py
"""सत्यापित कानूनी ज्ञान खोज के request/response models."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class LegalResearchQuery(BaseModel):
    """केवल verified corpus में खोज का अनुरोध."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=250)
    limit: int = Field(default=10, ge=1, le=25)


class LegalEvidence(BaseModel):
    """खोज से मिला traceable कानूनी स्रोत."""

    document_id: str
    title: str
    canonical_url: str
    authority: str | None = None
    decision_date: date | None = None
    document_type: str
    excerpt: str
    content_sha256: str | None = None
    verification_status: str = "verified"


class LegalResearchResponse(BaseModel):
    """स्रोत-सहित खोज परिणाम."""

    query: str
    results: list[LegalEvidence]
    result_count: int
    note: str
