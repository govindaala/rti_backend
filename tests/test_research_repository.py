# रिपॉजिटरी पथ: rti_backend/tests/test_research_repository.py
"""कानूनी खोज repository के SQL और परिणाम mapping के परीक्षण."""

from contextlib import contextmanager

from app.repositories import legal_knowledge


class FakeCursor:
    """Database cursor का छोटा deterministic test double."""

    def __init__(self) -> None:
        self.sql = ""
        self.params = ()

    def execute(self, sql: str, params: tuple) -> None:
        self.sql = sql
        self.params = params

    def fetchall(self) -> list[tuple]:
        return [
            (
                "doc-1",
                "सूचना का अधिकार आदेश",
                "https://cic.gov.in/orders/1",
                "CIC",
                None,
                "order",
                "धारा 8 के अंतर्गत सूचना पर विचार",
                "a" * 64,
            )
        ]


class FakeConnection:
    """Cursor context manager उपलब्ध कराए."""

    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    @contextmanager
    def cursor(self):
        yield self.fake_cursor


def test_search_uses_ranked_full_text_and_verified_filter(monkeypatch) -> None:
    """खोज relevance ranking और verified-only filter का उपयोग करे."""
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(legal_knowledge, "get_connection", lambda: connection)

    results = legal_knowledge.search_verified_documents("  सूचना   का अधिकार ", 7)

    assert len(results) == 1
    assert results[0]["document_id"] == "doc-1"
    assert results[0]["content_sha256"] == "a" * 64
    assert "websearch_to_tsquery" in cursor.sql
    assert "d.status = 'verified'" in cursor.sql
    assert "ORDER BY relevance DESC" in cursor.sql
    assert cursor.params == (
        "सूचना का अधिकार",
        "%सूचना का अधिकार%",
        "%सूचना का अधिकार%",
        "%सूचना का अधिकार%",
        "%सूचना का अधिकार%",
        7,
    )


def test_empty_query_does_not_connect_to_database(monkeypatch) -> None:
    """खाली query पर database connection न खुले."""
    def unexpected_connection():
        raise AssertionError("empty query must not open a database connection")

    monkeypatch.setattr(legal_knowledge, "get_connection", unexpected_connection)
    assert legal_knowledge.search_verified_documents("   ") == []
