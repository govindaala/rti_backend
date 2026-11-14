"""Tests for the optional FreeLLMAPI/OpenAI-compatible gateway."""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import llm_gateway


def _research():
    from app.models.research import LegalApplicationResponse
    return LegalApplicationResponse(
        question="क्या PIO पर विलंब के लिए दंड लग सकता है?", role="applicant",
        evidence=[{"document_id":"verified-1","title":"CIC order",
                   "canonical_url":"https://cic.gov.in/order/1","legal_issue":"विलंब",
                   "holding":"कारणों की जाँच आवश्यक","relevance_label":"strong_concept_match"}],
        direct_answer="सीधा जवाब: सत्यापित सामग्री सीमित है।", disclaimer="प्रारंभिक शोध।",
        common_legal_checks=[], role_specific_checks=[], limitations=[], result_count=1)


def _mock_settings(monkeypatch, **overrides):
    values = {"llm_api_base_url":"https://llm.example/v1", "llm_api_key":"test-key",
              "llm_model":"test-model", "llm_timeout_seconds":12}
    values.update(overrides)
    monkeypatch.setattr(llm_gateway, "settings", SimpleNamespace(**values))


def test_gateway_sends_verified_context_and_accepts_valid_citations(monkeypatch):
    captured = {}
    class FakeClient:
        def __init__(self, timeout): captured["timeout"] = timeout
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def post(self, url, headers, **kwargs):
            captured.update(url=url, headers=headers, body=kwargs["json"])
            return httpx.Response(200, request=httpx.Request("POST", url), json={"choices":[{"message":{"content":json.dumps({
                "answer":"धारा 20 की शर्तें जाँचना आवश्यक है।","source_ids":["verified-1"],
                "uncertainties":["आदेश का पूरा पाठ जाँचना होगा।"]},ensure_ascii=False)}}]})
    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx,"Client",FakeClient)
    result=llm_gateway.generate_grounded_answer(_research())
    assert result["source_ids"]==["verified-1"]
    assert result["status"]=="generated_with_verified_context"
    assert captured["url"]=="https://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"]=="Bearer test-key"
    assert "verified-1" in captured["body"]["messages"][1]["content"]
    assert "candidate_evidence" not in captured["body"]["messages"][1]["content"]


def test_gateway_rejects_citations_not_in_verified_context(monkeypatch):
    class FakeClient:
        def __init__(self, timeout): pass
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def post(self, *_args, **_kwargs):
            return httpx.Response(200, request=httpx.Request("POST", "https://llm.example/v1/chat/completions"), json={"choices":[{"message":{"content":json.dumps({
                "answer":"कानूनी उत्तर","source_ids":["invented-id"],"uncertainties":[]})}}]})
    _mock_settings(monkeypatch)
    monkeypatch.setattr(llm_gateway.httpx,"Client",FakeClient)
    with pytest.raises(llm_gateway.LLMGatewayError,match="citation"):
        llm_gateway.generate_grounded_answer(_research())


def test_gateway_disabled_without_credentials(monkeypatch):
    _mock_settings(monkeypatch, llm_api_base_url=None, llm_api_key=None, llm_model=None)
    with pytest.raises(llm_gateway.LLMGatewayError,match="not configured"):
        llm_gateway.generate_grounded_answer(_research())
