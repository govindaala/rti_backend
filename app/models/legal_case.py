# रिपॉजिटरी पथ: rti_backend/app/models/legal_case.py
"""न्यायिक निर्णयों को प्रमाण सहित संरचित रूप में रखने के मॉडल."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class VerificationStatus(str, Enum):
    """कानूनी रिकॉर्ड की समीक्षा की स्थिति."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class LegalCitation(BaseModel):
    """कानूनी निष्कर्ष के समर्थन में मूल स्रोत का संदर्भ."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: HttpUrl
    pinpoint: str = Field(
        min_length=1,
        description="निर्णय का पैरा, पृष्ठ, आदेश संख्या या अधिनियम की धारा",
    )
    summary: str = Field(min_length=1)
    verified: bool = False


class LegalIssue(BaseModel):
    """एक निर्णय के भीतर किसी एक कानूनी प्रश्न का अलग विश्लेषण."""

    model_config = ConfigDict(extra="forbid")

    issue: str = Field(min_length=1)
    applicant_arguments_accepted: list[str] = Field(default_factory=list)
    pio_arguments_accepted: list[str] = Field(default_factory=list)
    applicant_arguments_rejected: list[str] = Field(default_factory=list)
    pio_arguments_rejected: list[str] = Field(default_factory=list)
    legal_principles: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    outcome: str = ""
    citation_ids: list[str] = Field(default_factory=list)


class LegalCase(BaseModel):
    """एक निर्णय का स्रोत-सहित रिकॉर्ड; पूरे केस को एकतरफा न मानें."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    forum: str = Field(min_length=1)
    case_title: str = Field(min_length=1)
    decision_date: date | None = None
    issues: list[LegalIssue] = Field(min_length=1)
    citations: list[LegalCitation] = Field(min_length=1)
    verification_status: VerificationStatus = VerificationStatus.PENDING

    @model_validator(mode="after")
    def validate_citation_integrity(self) -> "LegalCase":
        """सुनिश्चित करें कि हर issue का citation मौजूद और सही रिकॉर्ड में हो."""
        citation_ids = {citation.citation_id for citation in self.citations}

        for issue in self.issues:
            missing_ids = set(issue.citation_ids) - citation_ids
            if missing_ids:
                raise ValueError(
                    f"अज्ञात citation_id: {', '.join(sorted(missing_ids))}"
                )

        # सत्यापित केस में कम-से-कम एक सत्यापित मूल स्रोत अनिवार्य है।
        if self.verification_status == VerificationStatus.VERIFIED:
            if not any(citation.verified for citation in self.citations):
                raise ValueError("सत्यापित केस के लिए सत्यापित citation आवश्यक है")

        return self
