# Repository path: rti_backend/app/models/legal_principle.py
"""Human-reviewed legal principle memory request/response models."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class PrincipleType(str, Enum):
    RATIO = "ratio_decidendi"
    OBITER = "obiter_dicta"
    PROCEDURAL = "procedural_direction"


class LegalStatus(str, Enum):
    PENDING = "pending_review"
    VERIFIED = "verified_current"
    NEEDS_REVIEW = "needs_subsequent_review"
    DISTINGUISHED = "distinguished"
    OVERRULED = "overruled"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class PinpointCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pinpoint: str = Field(min_length=1, max_length=100)
    supporting_note: str = Field(min_length=8, max_length=500)


class PrincipleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    issue: str = Field(min_length=8, max_length=1000)
    principle_type: PrincipleType
    principle_text: str = Field(min_length=20, max_length=3000)
    scope: str | None = Field(default=None, max_length=1500)
    conditions: list[str] = Field(default_factory=list, max_length=20)
    exceptions: list[str] = Field(default_factory=list, max_length=20)
    applicant_arguments_accepted: list[str] = Field(default_factory=list, max_length=20)
    applicant_arguments_rejected: list[str] = Field(default_factory=list, max_length=20)
    pio_arguments_accepted: list[str] = Field(default_factory=list, max_length=20)
    pio_arguments_rejected: list[str] = Field(default_factory=list, max_length=20)
    outcome: str | None = Field(default=None, max_length=1000)
    pinpoint_citations: list[PinpointCitation] = Field(min_length=1, max_length=20)


class PrincipleReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_status: LegalStatus
    reviewer_note: str = Field(min_length=20, max_length=1500)
    confirm_reviewed: bool
    superseded_by_document_id: UUID | None = None
    subsequent_treatment: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_review(self):
        self.reviewer_note = self.reviewer_note.strip()
        if len(self.reviewer_note) < 20:
            raise ValueError("समीक्षा टिप्पणी कम से कम 20 अक्षरों की होनी चाहिए")
        if not self.confirm_reviewed:
            raise ValueError("स्पष्ट मानव समीक्षा की पुष्टि आवश्यक है")
        if self.legal_status in {LegalStatus.OVERRULED, LegalStatus.SUPERSEDED}:
            if self.superseded_by_document_id is None:
                raise ValueError("Overruled/Superseded स्थिति के लिए बाद का निर्णय आवश्यक है")
        elif self.superseded_by_document_id is not None:
            raise ValueError("बाद का निर्णय केवल overruled/superseded स्थिति में दें")
        return self
