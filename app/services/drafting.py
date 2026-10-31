# रिपॉजिटरी पथ: rti_backend/app/services/drafting.py
"""RTI आवेदन का स्पष्ट, user-editable प्रारूप तैयार करें."""

from app.models.drafts import DraftLanguage, FirstAppealDraftRequest, RTIDraftRequest


def build_rti_draft(payload: RTIDraftRequest) -> str:
    """धारा 6(1) के अंतर्गत draft लौटाएँ; आवेदन कहीं submit न करें."""
    period = ""
    if payload.period_from or payload.period_to:
        period = (
            f"अवधि: {payload.period_from or 'निर्दिष्ट नहीं'} से "
            f"{payload.period_to or 'निर्दिष्ट नहीं'}\n"
            if payload.language == DraftLanguage.HINDI
            else f"Period: {payload.period_from or 'not specified'} to "
            f"{payload.period_to or 'not specified'}\n"
        )

    if payload.language == DraftLanguage.HINDI:
        points = "\n".join(
            f"{index}. {item}" for index, item in enumerate(payload.information_requested, 1)
        )
        return (
            f"सेवा में,\nलोक सूचना अधिकारी,\n{payload.public_authority}\n\n"
            f"विषय: {payload.subject}\n\n"
            "महोदय/महोदया,\n"
            "सूचना का अधिकार अधिनियम, 2005 की धारा 6(1) के अंतर्गत कृपया निम्नलिखित "
            "उपलब्ध अभिलेखों/सूचनाओं की प्रमाणित प्रतियाँ अथवा उपलब्ध सूचना प्रदान करें:\n\n"
            f"{period}{points}\n\n"
            "यदि माँगी गई सूचना का कोई भाग आपके प्राधिकरण के पास उपलब्ध नहीं है और "
            "किसी अन्य लोक प्राधिकरण के पास है, तो लागू होने पर अधिनियम की धारा 6(3) "
            "के अनुसार संबंधित भाग स्थानांतरित कर इसकी सूचना दें। यदि किसी सूचना पर "
            "छूट लागू मानी जाती है, तो कृपया लागू वैधानिक प्रावधान और कारण स्पष्ट करें "
            "तथा पृथक की जा सकने वाली शेष सूचना प्रदान करें।\n\n"
            "निर्धारित आवेदन शुल्क/भुगतान का विवरण संलग्न है (जहाँ लागू हो)। "
            "अतिरिक्त शुल्क होने पर नियमानुसार सूचित करें।\n\n"
            f"आवेदक: {payload.applicant_name}\nपता: {payload.postal_address}\n"
            "दिनांक: __________\nहस्ताक्षर: __________\n"
        )

    points = "\n".join(
        f"{index}. {item}" for index, item in enumerate(payload.information_requested, 1)
    )
    return (
        "To,\nThe Public Information Officer,\n"
        f"{payload.public_authority}\n\nSubject: {payload.subject}\n\n"
        "Sir/Madam,\n"
        "Under Section 6(1) of the Right to Information Act, 2005, "
        "please provide copies of the following records/information available with "
        "your public authority:\n\n"
        f"{period}{points}\n\n"
        "If any part of the requested information is held by another public authority, "
        "please transfer that part under Section 6(3), where applicable, and inform me. "
        "If any exemption is claimed, please specify the exact statutory provision and "
        "reasons, and disclose any reasonably severable non-exempt portion.\n\n"
        "Prescribed application fee/payment details are enclosed, where applicable. "
        "Please intimate any additional fee in accordance with the applicable rules.\n\n"
        f"Applicant: {payload.applicant_name}\nAddress: {payload.postal_address}\n"
        "Date: __________\nSignature: __________\n"
    )


def build_first_appeal_draft(payload: FirstAppealDraftRequest) -> str:
    """धारा 19(1) की प्रथम अपील का संपादन योग्य मसौदा बनाएँ."""
    grounds = "\\n".join(
        f"{index}. {item}" for index, item in enumerate(payload.grounds, 1)
    )
    reply_date = payload.pio_reply_date or (
        "उत्तर प्राप्त नहीं" if payload.language == DraftLanguage.HINDI else "No reply received"
    )
    if payload.language == DraftLanguage.HINDI:
        return (
            f"सेवा में,\\nप्रथम अपीलीय प्राधिकारी,\\n{payload.first_appellate_authority}\\n"
            f"{payload.public_authority}\\n\\n"
            "विषय: सूचना का अधिकार अधिनियम, 2005 की धारा 19(1) के अंतर्गत प्रथम अपील।\\n\\n"
            "महोदय/महोदया,\\n"
            f"मैंने दिनांक {payload.rti_application_date} को लोक सूचना अधिकारी को RTI आवेदन "
            f"प्रस्तुत किया था। PIO का उत्तर: {reply_date}। "
            "प्राप्त उत्तर/उत्तर न मिलने से असंतुष्ट होकर निम्न आधारों पर यह प्रथम अपील "
            "प्रस्तुत कर रहा/रही हूँ:\\n\\n"
            f"{grounds}\\n\\n"
            f"माँगी गई राहत: {payload.relief_sought}\\n\\n"
            "कृपया अभिलेखों और लागू कानून के आधार पर कारणयुक्त आदेश पारित करें तथा "
            "जहाँ आवश्यक हो सुनवाई का अवसर दें।\\n\\n"
            f"अपीलकर्ता: {payload.applicant_name}\\nपता: {payload.postal_address}\\n"
            "दिनांक: __________\\nहस्ताक्षर: __________\\n"
        )
    return (
        f"To,\\nThe First Appellate Authority,\\n{payload.first_appellate_authority}\\n"
        f"{payload.public_authority}\\n\\n"
        "Subject: First appeal under Section 19(1) of the Right to Information Act, 2005.\\n\\n"
        "Sir/Madam,\\n"
        f"I submitted an RTI application to the PIO on {payload.rti_application_date}. "
        f"PIO response: {reply_date}. Being aggrieved by the response/non-response, "
        "I submit this first appeal on the following grounds:\\n\\n"
        f"{grounds}\\n\\nRelief sought: {payload.relief_sought}\\n\\n"
        "Please pass a reasoned order after considering the records and applicable law, "
        "and provide an opportunity of hearing where appropriate.\\n\\n"
        f"Appellant: {payload.applicant_name}\\nAddress: {payload.postal_address}\\n"
        "Date: __________\\nSignature: __________\\n"
    )
