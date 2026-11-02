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
    """संक्षिप्त ज्ञान-सार, स्रोत और सत्यापन स्थिति वाला साक्ष्य."""
    document_id: str
    title: str
    canonical_url: str
    authority: str | None = None
    decision_date: date | None = None
    document_type: str
    excerpt: str
    learned_summary: str | None = None
    legal_issue: str | None = None
    holding: str | None = None
    cited_sections: list[str] = Field(default_factory=list)
    content_sha256: str | None = None
    verification_status: str = "verified"


class LegalResearchResponse(BaseModel):
    """स्रोत-सहित खोज परिणाम."""
    query: str
    results: list[LegalEvidence]
    result_count: int
    note: str


class LegalApplicationRequest(BaseModel):
    """नए तथ्य पर verified corpus के निर्णय लागू करने का पारदर्शी अनुरोध."""
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=8, max_length=2000)
    role: str = Field(default="applicant", pattern="^(applicant|pio|neutral)$")
    limit: int = Field(default=8, ge=1, le=15)


class AppliedLegalEvidence(BaseModel):
    """प्रासंगिकता संकेत और सत्यापित निर्णय का traceable reference."""
    document_id: str
    title: str
    canonical_url: str
    authority: str | None = None
    decision_date: date | None = None
    legal_issue: str | None = None
    holding: str | None = None
    cited_sections: list[str] = Field(default_factory=list)
    content_sha256: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    relevance_label: str


class AppliedLegalPrinciple(BaseModel):
    """वर्तमान verified ratio और उसके pinpoint citations."""
    principle_id: str
    document_id: str
    source_title: str
    source_url: str
    authority: str | None = None
    decision_date: date | None = None
    issue: str
    principle_text: str
    scope: str | None = None
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    applicant_arguments_accepted: list[str] = Field(default_factory=list)
    applicant_arguments_rejected: list[str] = Field(default_factory=list)
    pio_arguments_accepted: list[str] = Field(default_factory=list)
    pio_arguments_rejected: list[str] = Field(default_factory=list)
    outcome: str | None = None
    pinpoint_citations: list[dict] = Field(default_factory=list)
    legal_status: str


class LegalApplicationResponse(BaseModel):
    """नए प्रश्न के लिए स्रोत-आधारित तुलनात्मक विश्लेषण."""
    question: str
    role: str
    evidence: list[AppliedLegalEvidence]
    verified_principles: list[AppliedLegalPrinciple] = Field(default_factory=list)
    common_legal_checks: list[str]
    role_specific_checks: list[str]
    limitations: list[str]
    result_count: int
