# रिपॉजिटरी पथ: rti_backend/tests/test_drafting.py
"""RTI draft और analysis checklist endpoints के परीक्षण."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_hindi_rti_draft_is_generated_but_never_submitted() -> None:
    """Hindi draft में आवश्यक संरचना हो और auto-filing false रहे."""
    response = client.post(
        "/api/v1/drafts/rti",
        json={
            "language": "hi",
            "public_authority": "जिला शिक्षा अधिकारी, मंदसौर",
            "applicant_name": "परीक्षण आवेदक",
            "postal_address": "ग्राम परीक्षण, तहसील परीक्षण, मध्य प्रदेश",
            "subject": "विद्यालय में स्वीकृत पदों की जानकारी",
            "information_requested": [
                "विद्यालयवार स्वीकृत और भरे हुए पदों की प्रमाणित सूची दें",
                "पिछले तीन वर्षों की नियुक्ति आदेशों की प्रतियाँ दें",
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert body["submitted"] is False
    assert "धारा 6(1)" in body["draft"]
    assert "स्वीकृत और भरे हुए पदों" in body["draft"]


def test_draft_rejects_empty_information_points() -> None:
    """रिक्त सूचना-बिंदु पर validation error आए."""
    response = client.post(
        "/api/v1/drafts/rti",
        json={
            "public_authority": "नगर परिषद",
            "applicant_name": "परीक्षण आवेदक",
            "postal_address": "परीक्षण पता",
            "subject": "रिकॉर्ड की जानकारी",
            "information_requested": [""],
        },
    )
    assert response.status_code == 422


def test_analysis_checklist_is_role_specific_and_disclaims_final_opinion() -> None:
    """Applicant checklist और सीमाएँ स्पष्ट लौटें."""
    response = client.post(
        "/api/v1/analysis/checklist",
        json={
            "role": "applicant",
            "facts": "मैंने नगर परिषद से पिछले तीन वर्षों के निर्माण कार्यों के रिकॉर्ड माँगे।",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "applicant"
    assert any("प्रथम अपील" in item for item in body["checklist"])
    assert "अंतिम कानूनी राय" in body["notice"]


def test_first_appeal_draft_is_not_submitted() -> None:
    """First appeal draft carries Section 19(1) and remains user-controlled."""
    response = client.post(
        "/api/v1/drafts/first-appeal",
        json={
            "language": "hi",
            "public_authority": "जिला शिक्षा अधिकारी",
            "first_appellate_authority": "संयुक्त संचालक, शिक्षा",
            "applicant_name": "परीक्षण आवेदक",
            "postal_address": "परीक्षण पता, मध्य प्रदेश",
            "rti_application_date": "01-10-2026",
            "pio_reply_date": "25-10-2026",
            "grounds": ["माँगी गई दो सूचनाओं में से एक का उत्तर नहीं दिया गया"],
            "relief_sought": "बिंदु 2 की प्रमाणित सूचना उपलब्ध कराई जाए",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submitted"] is False
    assert "धारा 19(1)" in body["draft"]
    assert "बिंदु 2" in body["draft"]
