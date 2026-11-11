# Repository path: rti_backend/tests/test_research_repository.py
"""कानूनी खोज repository के SQL और परिणाम mapping के परीक्षण."""

from contextlib import contextmanager

from app.repositories import legal_knowledge


class FakeCursor:
    def __init__(self) -> None:
        self.sql = ""
        self.params = ()

    def execute(self, sql: str, params: tuple) -> None:
        self.sql = sql
        self.params = params

    def fetchall(self) -> list[tuple]:
        return [(
            "doc-1", "सूचना का अधिकार आदेश", "https://cic.gov.in/orders/1",
            "CIC", None, "order",
            "संक्षिप्त ज्ञान-सार: धारा 8(1)(j); मानव समीक्षा आवश्यक।",
            "a" * 64,
            "संक्षिप्त ज्ञान-सार: धारा 8(1)(j); मानव समीक्षा आवश्यक।",
            "व्यक्तिगत सूचना से जुड़ा मुद्दा", "अपील खारिज होने का संकेत",
            ["धारा 8(1)(j)"], [],
        )]


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    @contextmanager
    def cursor(self):
        yield self.fake_cursor


def test_search_uses_ranked_full_text_and_returns_structured_knowledge(monkeypatch) -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(legal_knowledge, "get_connection", lambda: connection)

    results = legal_knowledge.search_verified_documents("  सूचना   का अधिकार ", 7)

    assert len(results) == 1
    assert results[0]["document_id"] == "doc-1"
    assert results[0]["content_sha256"] == "a" * 64
    assert results[0]["learned_summary"].startswith("संक्षिप्त ज्ञान-सार")
    assert results[0]["cited_sections"] == ["धारा 8(1)(j)"]
    assert results[0]["decision_candidates"] == []
    assert results[0]["verification_status"] == "verified"
    assert "websearch_to_tsquery" in cursor.sql
    assert "d.status = 'verified'" in cursor.sql
    assert "ORDER BY relevance DESC" in cursor.sql
    assert "COALESCE(d.learned_summary" in cursor.sql
    assert cursor.params == (
        "सूचना का अधिकार",
        "%सूचना का अधिकार%", "%सूचना का अधिकार%", "%सूचना का अधिकार%",
        "%सूचना का अधिकार%", "%सूचना का अधिकार%", "%सूचना का अधिकार%",
        "%सूचना का अधिकार%", "%सूचना का अधिकार%", "%सूचना का अधिकार%",
        "%सूचना का अधिकार%", 7,
    )


def test_empty_query_does_not_connect_to_database(monkeypatch) -> None:
    def unexpected_connection():
        raise AssertionError("empty query must not open a database connection")

    monkeypatch.setattr(legal_knowledge, "get_connection", unexpected_connection)
    assert legal_knowledge.search_verified_documents("   ") == []



def test_candidate_search_returns_machine_extracted_rows_without_verifying_them(monkeypatch) -> None:
    cursor = FakeCursor()
    cursor.fetchall = lambda: [(
        "candidate-1", "CIC candidate order", "https://cic.gov.in/orders/candidate-1",
        "CIC", None, "order", "धारा 8 का candidate excerpt", "d" * 64,
        "machine summary", "धारा 8", None, ["धारा 8"],
        [{
            "kind": "finding_candidate",
            "excerpt": "The Commission observes that the exemption must be justified.",
            "paragraph_reference": "पैरा 9",
            "review_status": "human_review_required",
        }],
        "human_review_required", "rule_based_structured_v3", "extracted",
    )]
    monkeypatch.setattr(
        legal_knowledge, "get_connection", lambda: FakeConnection(cursor)
    )

    results = legal_knowledge.search_candidate_documents("धारा 8", 4)

    assert len(results) == 1
    assert results[0]["verification_status"] == "machine_extracted_candidate"
    assert results[0]["analysis_status"] == "human_review_required"
    assert results[0]["analysis_method"] == "rule_based_structured_v3"
    assert results[0]["decision_candidates"][0]["paragraph_reference"] == "पैरा 9"
    assert "d.status = 'review_required'" in cursor.sql
    assert "d.analysis_status = 'human_review_required'" in cursor.sql
    assert "d.status = 'verified'" not in cursor.sql
    assert cursor.params == ("धारा 8", "%धारा 8%", 4)


def test_empty_candidate_query_does_not_connect_to_database(monkeypatch) -> None:
    def unexpected_connection():
        raise AssertionError("empty query must not open a database connection")

    monkeypatch.setattr(legal_knowledge, "get_connection", unexpected_connection)
    assert legal_knowledge.search_candidate_documents("   ") == []
