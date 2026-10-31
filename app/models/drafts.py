# रिपॉजिटरी पथ: rti_backend/app/models/drafts.py
"""RTI आवेदन का user-reviewed draft बनाने के input models."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DraftLanguage(str, Enum):
    """ड्राफ्ट की भाषा."""

    HINDI = "hi"
    ENGLISH = "en"


class RTIDraftRequest(BaseModel):
    """केवल draft बनाने हेतु आवश्यक विवरण; कोई auto-filing नहीं."""

    model_config = ConfigDict(extra="forbid")

    language: DraftLanguage = DraftLanguage.HINDI
    public_authority: str = Field(min_length=2, max_length=180)
    applicant_name: str = Field(min_length=2, max_length=120)
    postal_address: str = Field(min_length=5, max_length=1000)
    subject: str = Field(min_length=5, max_length=240)
    information_requested: list[str] = Field(min_length=1, max_length=20)
    period_from: str | None = Field(default=None, max_length=40)
    period_to: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def validate_information_points(self) -> "RTIDraftRequest":
        """खाली या अत्यधिक छोटे सूचना-बिंदु स्वीकार न हों."""
        cleaned = [item.strip() for item in self.information_requested]
        if any(len(item) < 5 or len(item) > 1200 for item in cleaned):
            raise ValueError("हर सूचना-बिंदु 5 से 1200 अक्षरों के बीच होना चाहिए")
        self.information_requested = cleaned
        return self
