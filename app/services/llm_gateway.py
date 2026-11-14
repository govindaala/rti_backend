"""Optional OpenAI-compatible LLM gateway for source-grounded RTI answers."""
from __future__ import annotations
import json
from typing import Any
import httpx
from app.core.config import settings
from app.models.research import LegalApplicationResponse


class LLMGatewayError(RuntimeError):
    """The optional external LLM gateway is unavailable or returned invalid data."""


def _verified_context(research: LegalApplicationResponse) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence = [
        {"id": item.document_id, "title": item.title, "authority": item.authority,
         "date": item.decision_date.isoformat() if item.decision_date else None,
         "url": item.canonical_url, "legal_issue": item.legal_issue, "holding": item.holding,
         "sections": item.cited_sections, "content_sha256": item.content_sha256,
         "verification_status": "verified"}
        for item in research.evidence if item.document_id and item.canonical_url
    ]
    principles = [
        {"id": item.principle_id, "document_id": item.document_id, "source_title": item.source_title,
         "source_url": item.source_url, "issue": item.issue, "principle": item.principle_text,
         "scope": item.scope, "conditions": item.conditions, "exceptions": item.exceptions,
         "pinpoint_citations": item.pinpoint_citations, "legal_status": item.legal_status}
        for item in research.verified_principles
        if item.legal_status == "verified_current" and item.source_url
    ]
    return evidence, principles


def generate_grounded_answer(research: LegalApplicationResponse) -> dict[str, Any]:
    """Generate a Hindi answer while constraining citations to supplied verified IDs."""
    if not settings.llm_api_base_url or not settings.llm_api_key or not settings.llm_model:
        raise LLMGatewayError("LLM gateway is not configured")
    evidence, principles = _verified_context(research)
    allowed_ids = {item["id"] for item in evidence}
    allowed_ids.update(item["id"] for item in principles)
    if not allowed_ids:
        return {"answer": research.direct_answer, "source_ids": [],
                "uncertainties": research.fact_gaps or ["सत्यापित स्रोत उपलब्ध नहीं हैं।"],
                "model": None, "status": "insufficient_verified_material"}
    system_prompt = (
        "आप RTI कानून के शोध सहायक हैं। केवल दिए गए VERIFIED_CONTEXT से उत्तर दें। "
        "किसी धारा, निर्णय, तारीख, उद्धरण या कानूनी नियम का आविष्कार न करें। "
        "संदर्भ में तथ्य न हो तो उसे अज्ञात कहें। Applicant और PIO दोनों के वैध तर्क "
        "निष्पक्षता से रखें। अंतिम कानूनी राय न दें। उत्तर हिन्दी में दें। "
        "केवल JSON object लौटाएँ: answer (string), source_ids (string array containing "
        "only supplied evidence/principle IDs), uncertainties (string array). "
        "Machine-extracted candidates और unverified सामग्री का उपयोग न करें."
    )
    user_payload = {"question": research.question, "requested_role": research.role,
                    "verified_evidence": evidence, "verified_current_principles": principles,
                    "baseline_checks": research.answer_guidance, "known_fact_gaps": research.fact_gaps}
    url = settings.llm_api_base_url.rstrip("/") + "/chat/completions"
    body = {"model": settings.llm_model, "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}]}
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(url, headers={"Authorization": f"Bearer {settings.llm_api_key}"}, json=body)
            response.raise_for_status()
            payload = response.json()
        parsed = json.loads(payload["choices"][0]["message"]["content"])
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMGatewayError("LLM gateway request failed or returned invalid JSON") from exc
    answer, source_ids, uncertainties = parsed.get("answer"), parsed.get("source_ids", []), parsed.get("uncertainties", [])
    if not isinstance(answer, str) or not answer.strip():
        raise LLMGatewayError("LLM gateway response did not contain an answer")
    if not isinstance(source_ids, list) or any(not isinstance(item, str) or item not in allowed_ids for item in source_ids):
        raise LLMGatewayError("LLM gateway returned a citation outside verified context")
    if not isinstance(uncertainties, list) or any(not isinstance(item, str) for item in uncertainties):
        raise LLMGatewayError("LLM gateway returned invalid uncertainty metadata")
    return {"answer": answer.strip(), "source_ids": list(dict.fromkeys(source_ids)),
            "uncertainties": uncertainties, "model": settings.llm_model,
            "status": "generated_with_verified_context"}
