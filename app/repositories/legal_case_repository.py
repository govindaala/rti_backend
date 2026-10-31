# रिपॉजिटरी पथ: rti_backend/app/repositories/legal_case_repository.py
"""SQLite में कानूनी केस रिकॉर्ड रखने का अपना repository adapter."""

import json
import sqlite3
from pathlib import Path

from app.models.legal_case import LegalCase


class DuplicateLegalCaseError(Exception):
    """जब समान case_id पहले से मौजूद हो."""


class LegalCaseRepository:
    """Python के built-in sqlite3 से केस रिकॉर्ड create और read करें."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        # कनेक्शन/टेबल केवल अपने ऐप के SQLite फाइल में बनते हैं।
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS legal_cases (
                    case_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        """हर operation के लिए नया SQLite connection बनाएँ."""
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, case: LegalCase) -> str:
        """नया केस जोड़ें; पुराने रिकॉर्ड को overwrite न करें."""
        payload = json.dumps(
            case.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO legal_cases (case_id, payload_json) VALUES (?, ?)",
                    (case.case_id, payload),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateLegalCaseError(case.case_id) from exc
        return case.case_id

    def get(self, case_id: str) -> LegalCase | None:
        """case_id से केस पढ़ें; रिकॉर्ड न मिलने पर None लौटाएँ."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM legal_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            return None
        return LegalCase.model_validate(json.loads(row["payload_json"]))
