# रिपॉजिटरी पथ: rti_backend/tests/test_legal_case_repository.py
"""SQLite repository के वास्तविक, अस्थायी database पर unit tests."""

import pytest

from app.models.legal_case import LegalCase
from app.repositories.legal_case_repository import (
    DuplicateLegalCaseError,
    LegalCaseRepository,
)


def sample_case() -> LegalCase:
    """एक वैध, काल्पनिक केस मॉडल बनाएँ."""
    return LegalCase.model_validate(
        {
            "case_id": "SQLITE-TEST-001",
            "forum": "High Court",
            "case_title": "काल्पनिक परीक्षण निर्णय",
            "issues": [{"issue": "क्या सूचना दी जानी चाहिए?", "citation_ids": ["C1"]}],
            "citations": [
                {
                    "citation_id": "C1",
                    "source_title": "परीक्षण स्रोत",
                    "source_url": "https://cic.gov.in/example",
                    "pinpoint": "पैरा 1",
                    "summary": "केवल परीक्षण हेतु",
                    "verified": False,
                }
            ],
        }
    )


def test_repository_creates_and_reads_case(tmp_path) -> None:
    """केस create करने के बाद वही रिकॉर्ड वापस पढ़ा जा सके."""
    repository = LegalCaseRepository(tmp_path / "legal_cases.sqlite3")
    case = sample_case()

    assert repository.create(case) == case.case_id
    loaded = repository.get(case.case_id)

    assert loaded is not None
    assert loaded.case_id == case.case_id
    assert loaded.issues[0].issue == case.issues[0].issue
    assert str(loaded.citations[0].source_url) == str(case.citations[0].source_url)


def test_repository_does_not_overwrite_existing_case(tmp_path) -> None:
    """डुप्लीकेट case_id पर overwrite की जगह स्पष्ट त्रुटि मिले."""
    repository = LegalCaseRepository(tmp_path / "legal_cases.sqlite3")
    case = sample_case()
    repository.create(case)

    with pytest.raises(DuplicateLegalCaseError):
        repository.create(case)


def test_repository_returns_none_for_missing_case(tmp_path) -> None:
    """अनुपस्थित रिकॉर्ड को अपवाद की जगह None के रूप में लौटाएँ."""
    repository = LegalCaseRepository(tmp_path / "legal_cases.sqlite3")

    assert repository.get("NOT-FOUND") is None
