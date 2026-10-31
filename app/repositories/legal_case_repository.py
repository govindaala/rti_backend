# रिपॉजिटरी पथ: rti_backend/app/repositories/legal_case_repository.py
"""Firestore में कानूनी केस रिकॉर्ड सुरक्षित रखने का repository adapter."""

from typing import Any

from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from app.models.legal_case import LegalCase


class DuplicateLegalCaseError(Exception):
    """जब समान case_id पहले से मौजूद हो."""


class LegalCaseRepository:
    """Firestore client के माध्यम से केस रिकॉर्ड create और read करें."""

    def __init__(self, client: Any) -> None:
        # Client injection से Emulator और unit-test fake client उपयोग किए जा सकते हैं।
        self._collection = client.collection("legal_cases")

    def create(self, case: LegalCase) -> str:
        """नया केस create करें; पुराने रिकॉर्ड को चुपचाप overwrite न करें."""
        document = self._collection.document(case.case_id)
        payload = case.model_dump(mode="json")

        try:
            # Firestore create() मौजूद document को overwrite नहीं करता।
            document.create(payload)
        except AlreadyExists as exc:
            raise DuplicateLegalCaseError(case.case_id) from exc

        return case.case_id

    def get(self, case_id: str) -> LegalCase | None:
        """case_id से केस पढ़ें; अनुपस्थित रिकॉर्ड पर None लौटाएँ."""
        snapshot = self._collection.document(case_id).get()
        if not snapshot.exists:
            return None
        return LegalCase.model_validate(snapshot.to_dict())


def create_firestore_client(project_id: str | None) -> firestore.Client:
    """Application Default Credentials से Firestore client बनाएँ."""
    if not project_id:
        raise RuntimeError("FIRESTORE_PROJECT_ID environment variable सेट नहीं है")

    # Cloud Run/अन्य Google Cloud runtime में attached service account उपयोग होगा।
    # Local development में gcloud ADC या Firestore Emulator configure करें।
    return firestore.Client(project=project_id)
