# रिपॉजिटरी पथ: rti_backend/tests/test_legal_case_repository.py
"""Firestore repository के लिए नेटवर्क-रहित fake-client परीक्षण."""

import pytest
from google.api_core.exceptions import AlreadyExists

from app.models.legal_case import LegalCase
from app.repositories.legal_case_repository import (
    DuplicateLegalCaseError,
    LegalCaseRepository,
)


class FakeSnapshot:
    """Firestore document snapshot का छोटा परीक्षण विकल्प."""

    def __init__(self, data: dict | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict | None:
        return self._data


class FakeDocument:
    """Firestore document reference का परीक्षण विकल्प."""

    def __init__(self, store: dict, document_id: str) -> None:
        self.store = store
        self.document_id = document_id

    def create(self, payload: dict) -> None:
        if self.document_id in self.store:
            raise AlreadyExists("दस्तावेज़ पहले से मौजूद है")
        self.store[self.document_id] = payload

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self.store.get(self.document_id))


class FakeCollection:
    """Firestore collection reference का परीक्षण विकल्प."""

    def __init__(self, store: dict) -> None:
        self.store = store

    def document(self, document_id: str) -> FakeDocument:
        return FakeDocument(self.store, document_id)


class FakeFirestoreClient:
    """नेटवर्क के बिना Firestore व्यवहार का परीक्षण करें."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def collection(self, name: str) -> FakeCollection:
        assert name == "legal_cases"
        return FakeCollection(self.store)


def sample_case() -> LegalCase:
    """एक वैध, काल्पनिक केस मॉडल बनाएँ."""
    return LegalCase.model_validate(
        {
            "case_id": "FIRESTORE-TEST-001",
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


def test_repository_creates_and_reads_case() -> None:
    """केस create करने के बाद वही रिकॉर्ड वापस पढ़ा जा सके."""
    repository = LegalCaseRepository(FakeFirestoreClient())
    case = sample_case()

    assert repository.create(case) == case.case_id
    loaded = repository.get(case.case_id)

    assert loaded is not None
    assert loaded.case_id == case.case_id
    assert loaded.issues[0].issue == case.issues[0].issue
    assert str(loaded.citations[0].source_url) == str(case.citations[0].source_url)


def test_repository_does_not_overwrite_existing_case() -> None:
    """डुप्लीकेट case_id पर overwrite की जगह स्पष्ट त्रुटि मिले."""
    repository = LegalCaseRepository(FakeFirestoreClient())
    case = sample_case()
    repository.create(case)

    with pytest.raises(DuplicateLegalCaseError):
        repository.create(case)


def test_repository_returns_none_for_missing_case() -> None:
    """अनुपस्थित रिकॉर्ड को अपवाद की जगह None के रूप में लौटाएँ."""
    repository = LegalCaseRepository(FakeFirestoreClient())

    assert repository.get("NOT-FOUND") is None
