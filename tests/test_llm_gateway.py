"""Tests for the optional source-grounded OpenAI-compatible gateway."""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import llm_gateway


def _research():
    from app.models.research import LegalApplicationResponse

    return LegalApplicationResponse(
        question="क्या PIO पर विलंब के लिए दंड लग सकता है?",
        role="applicant",
        evidence=[
            {
                "document_id": "verified-1",
                "title": "CIC order",
                "canonical_url": "https://cic.gov.in/order/1",
                "legal_issue": "विलंब",
                "holding": "कारणों की जाँच आवश्यक",
                "relevance_label": "strong_concept_match",
            }
        ],
        verified_principles=[
            {
                "principle_id": "principle-1",
                "document_id": "verified-1",
                "source_title": "CIC order",
                "source_url": "https://cic.gov.in/order/1",
                "authority": "CIC",
                "issue": "विलंब और दंड",
                "principle_text": "धारा 20 की वैधानिक शर्तें स्थापित होनी चाहिए।",
                "scope": "धारा 20",
                "conditions": ["कारणयुक्त सुनवाई"],
                "exceptions": [],
                "applicant_arguments_accepted": ["देरी का प्रमाण"],
                "applicant_arguments_rejected": [],
                "pio_arguments_accepted": [],
                "pio_arguments_rejected": ["सिर्फ सामान्य स्पष्टीकरण"],
                "outcome": "आंशिक राहत",
                "pinpoint_citations": [{"paragraph": "7"}],
                "legal_status": "verified_current",
            }
        ],
        direct_answer="सीधा जवाब: सत्यापित सामग्री सीमित है।",
        legal_basis=[{"issue": "विलंब", "principle": "धारा 20 की शर्तें", "source": {"url": "https://cic.gov.in/order/1"}}],
        case_positions=[{"issue": "विलंब", "outcome": "आंशिक राहत"}],
        candidate_evidence=[
            {
                "document_id": "candidate-1",
                "title": "Unreviewed candidate",
                "canonical_url": "https://cic.gov.in/order/candidate-1",
                "verification_status": "machine_extracted_candidate",
            }
        ],
        candidate_case_positions=[{"source_url": "https://cic.gov.in/order/candidate-1"}],
        fact_gaps=["क्या PIO को आवेदन प्राप्त हुआ था?"],
        next_steps=["प्राप्ति तिथि और PIO का उत्तर मिलाकर प्रथम अपील में विलंब का मुद्दा उठाएँ।"],
        disclaimer="प्रारंभिक शोध।",
        common_legal_checks=[],
        role_specific_checks=[],
        limitations=[],
        result_count=1,
    )


def _mock_settings(monkeypatch, **overrides):
    values = {
        "llm_api_base_url": "https://llm.example/v1",
        "llm_api_key": "test-key",
        "llm_model": "test-model",
        "llm_timeout_seconds": 12,
    }
    values.update(overrides)
    monkeypatch.setattr(llm_gateway, "settings", SimpleNamespace(**values))


def _valid_model_response():
    return {
        "answer": "सीधा जवाब: उपलब्ध रिकॉर्ड में देरी का मुद्दा उठता है, लेकिन धारा 20 की शर्तें अलग से सिद्ध करनी होंगी।",
        "source_ids": ["verified-1", "principle-1"],
        "citations": [
            {"source_id": "verified-1", "claim": "CIC आदेश में विलंब का मुद्दा दर्ज है।", "pinpoint": None},
            {"source_id": "principle-1", "claim": "धारा 20 की शर्तें", "pinpoint": {"paragraph": "7"}},
        ],
        "fact_comparisons": [
            {
                "source_id": "principle-1",
                "applicability": "uncertain",
                "similarities": ["विलंब का प्रश्न दोनों मामलों में है।"],
                "differences": ["वर्तमान मामले की प्राप्ति तिथि उपलब्ध नहीं है।"],
                "reason": "निर्णय की शर्तें उपलब्ध तथ्य से पूरी तरह नहीं मिलतीं।",
                "pinpoint": {"paragraph": "7"},
            }
        ],
        "uncertainties": ["आवेदन प्राप्ति की तारीख की पुष्टि आवश्यक है।"],
        "next_steps": ["प्राप्ति प्रमाण के आधार पर प्रथम अपील में विलंब का मुद्दा उठाएँ।"],
    }


def test_gateway_sends_conclusion_first_analysis_and_accepts_verified_citations(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, headers, **kwargs):
            captured.update(url=url, headers=headers, body=kwargs["json"])
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": {"content": json.dumps(_valid_model_response(), ensure_ascii=False)}}]},
            )

    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx, "Client", FakeClient)
    result = llm_gateway.generate_grounded_answer(_research())

    payload = json.loads(captured["body"]["messages"][1]["content"])
    assert result["source_ids"] == ["verified-1", "principle-1"]
    assert result["status"] == "generated_with_verified_context"
    assert result["answer"].startswith("सीधा जवाब:")
    assert result["fact_comparisons"][0]["verification_status"] == "machine_extracted_candidate"
    assert result["citations"][1]["pinpoint"] == {"paragraph": "7"}
    assert result["next_steps"][0].startswith("प्राप्ति प्रमाण")
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert payload["deterministic_analysis"]["direct_answer"].startswith("सीधा जवाब:")
    assert payload["deterministic_analysis"]["legal_basis"]
    assert payload["verified_current_principles"][0]["applicant_arguments_accepted"]
    assert payload["verified_current_principles"][0]["pio_arguments_rejected"]
    assert payload["citation_index"][1]["pinpoints"] == [{"paragraph": "7"}]
    assert "candidate_evidence" not in payload
    assert "candidate_case_positions" not in payload
    assert "candidate-1" not in captured["body"]["messages"][1]["content"]
    assert "baseline_checks" not in payload


def test_gateway_rejects_citations_not_in_verified_context(monkeypatch):
    response = _valid_model_response()
    response["source_ids"] = ["invented-id"]

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            url = "https://llm.example/v1/chat/completions"
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": {"content": json.dumps(response, ensure_ascii=False)}}]},
            )

    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx, "Client", FakeClient)
    with pytest.raises(llm_gateway.LLMGatewayError, match="citation"):
        llm_gateway.generate_grounded_answer(_research())


def test_gateway_rejects_pinpoints_not_present_in_verified_source(monkeypatch):
    response = _valid_model_response()
    response["citations"][1]["pinpoint"] = {"paragraph": "999"}

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            url = "https://llm.example/v1/chat/completions"
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": {"content": json.dumps(response, ensure_ascii=False)}}]},
            )

    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx, "Client", FakeClient)
    with pytest.raises(llm_gateway.LLMGatewayError, match="pinpoint"):
        llm_gateway.generate_grounded_answer(_research())


def test_gateway_rejects_non_conclusion_first_answer(monkeypatch):
    response = _valid_model_response()
    response["answer"] = "सामान्य सलाह:"

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            url = "https://llm.example/v1/chat/completions"
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": {"content": json.dumps(response, ensure_ascii=False)}}]},
            )

    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx, "Client", FakeClient)
    with pytest.raises(llm_gateway.LLMGatewayError, match="conclusion-first"):
        llm_gateway.generate_grounded_answer(_research())


def test_gateway_rejects_answer_without_verified_citations(monkeypatch):
    response = _valid_model_response()
    response["source_ids"] = []
    response["citations"] = []

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            url = "https://llm.example/v1/chat/completions"
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": {"content": json.dumps(response, ensure_ascii=False)}}]},
            )

    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx, "Client", FakeClient)
    with pytest.raises(llm_gateway.LLMGatewayError, match="no verified citations"):
        llm_gateway.generate_grounded_answer(_research())


def test_gateway_requires_source_ids_to_match_citation_ids(monkeypatch):
    response = _valid_model_response()
    response["source_ids"] = ["verified-1"]

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            url = "https://llm.example/v1/chat/completions"
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": {"content": json.dumps(response, ensure_ascii=False)}}]},
            )

    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx, "Client", FakeClient)
    with pytest.raises(llm_gateway.LLMGatewayError, match="do not match citations"):
        llm_gateway.generate_grounded_answer(_research())


def test_gateway_disabled_without_credentials(monkeypatch):
    _mock_settings(monkeypatch, llm_api_base_url=None, llm_api_key=None, llm_model=None)
    with pytest.raises(llm_gateway.LLMGatewayError, match="not configured"):
        llm_gateway.generate_grounded_answer(_research())
