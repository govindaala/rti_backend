// रिपॉजिटरी पथ: rti_backend/web/app.js
"use strict";

// Applicant workspace सवाल को verified legal research API तक भेजता है।
const translations = {
  hi: {
    how:"कैसे काम करता है",language:"भाषा",eyebrow:"सूचना का अधिकार • कानून आधारित सहायता",
    heroTitle:"RTI के सवालों को समझें,\nकानून के आधार पर आगे बढ़ें।",
    heroText:"कानून, सरकारी आदेश और न्यायिक निर्णयों के स्रोत-आधारित अध्ययन के लिए एक स्वतंत्र मंच।",
    notFiling:"यह मंच आवेदन या अपील अपने-आप दाखिल नहीं करता।",free:"निःशुल्क",
    applicantTitle:"आवेदक सहायता",applicantText:"RTI आवेदन, PIO के जवाब, छूट की वैधता और प्रथम/द्वितीय अपील के विकल्पों को समझें।",
    startApplicant:"आवेदक के रूप में आगे बढ़ें",paid:"सदस्यता आधारित",pioTitle:"PIO सहायता",
    pioText:"वैधानिक समय-सीमा, लागू अपवाद, आंशिक प्रकटीकरण और कारणयुक्त जवाब का विश्लेषण करें।",
    startPio:"PIO सहायता देखें",workspaceLabel:"विश्लेषण कार्यक्षेत्र",close:"बंद करें",
    questionLabel:"आप किस RTI/कानूनी मुद्दे पर सहायता चाहते हैं?",questionPlaceholder:"अपना प्रश्न, PIO का जवाब या संबंधित कानूनी स्थिति लिखें...",
    documentsLabel:"दस्तावेज़ अपलोड (अभी उपलब्ध नहीं)",privacyHint:"आपका प्रश्न सत्यापित निर्णयों और मशीन-निकाले candidate स्रोतों में खोजा जाएगा। दोनों की स्थिति अलग दिखाई जाएगी.",
    submitQuestion:"कानूनी जवाब प्राप्त करें",resultTitle:"कानूनी उत्तर और स्रोत",loading:"कानूनी स्रोतों और निर्णयों का विश्लेषण...",completed:"कानूनी शोध परिणाम तैयार हैं।",error:"शोध सेवा से परिणाम नहीं मिले: ",answerDisclaimer:"सत्यापित सिद्धांत और मशीन-निकाले candidate अलग रखे गए हैं; candidate अंश को verified ratio या binding precedent न मानें। मूल स्रोत और वर्तमान कानून देखें।",candidateEvidenceTitle:"मशीन-निकाले स्रोत (अभी सत्यापित नहीं)",checklists:{applicant:["माँगी गई सूचना को अलग-अलग, स्पष्ट और पहचान योग्य अभिलेख-बिंदुओं में बाँटें।","आवेदन की तारीख, प्राप्ति का प्रमाण, शुल्क और संबंधित लोक प्राधिकरण जाँचें।","PIO के उत्तर/अस्वीकृति में उद्धृत प्रत्येक धारा और उसके आवश्यक तत्व जाँचें।","आंशिक प्रकटीकरण, अभिलेख निरीक्षण और उपलब्ध अपील/शिकायत उपायों पर विचार करें।","प्रथम अपील की समय-सीमा और सक्षम प्रथम अपीलीय प्राधिकारी की पुष्टि करें."],pio:["संबंधित शाखाओं और अभिलेख-धारकों में उचित रिकॉर्ड खोज का दस्तावेजीकरण करें।","सूचना उपलब्ध है, अस्तित्व में नहीं है, अन्य प्राधिकरण के पास है या नष्ट हुई—स्थिति अलग करें।","धारा 8/9 का कोई अपवाद लागू हो तो उसके प्रत्येक आवश्यक तत्व और वर्तमान न्यायिक व्याख्या जाँचें।","धारा 10 के तहत पृथक्करण/आंशिक प्रकटीकरण की संभावना जाँचें।","धारा 11 की third-party प्रक्रिया केवल जहाँ वैधानिक रूप से लागू हो वहाँ जाँचें।","उत्तर, शुल्क-सूचना और कारणयुक्त आदेश की वैधानिक समय-सीमा जाँचें."]},methodLabel:"हमारा तरीका",methodTitle:"स्रोत पहले, निष्कर्ष बाद में।",
    step1Title:"मूल स्रोत",step1Text:"अधिनियम, नियम, सरकारी आदेश और न्यायिक निर्णय।",
    step2Title:"मुद्दा-वार जाँच",step2Text:"हर कानूनी प्रश्न और दोनों पक्षों के तर्क अलग-अलग।",
    step3Title:"संदर्भ सहित उत्तर",step3Text:"धारा, पैरा और स्रोत की स्थिति स्पष्ट करके।",
    disclaimer:"यह सूचना-सहायक मंच है, वकील की सेवाओं का विकल्प नहीं।",
    decisionTitle:"निर्णय",authorityLabel:"न्यायालय/आयोग",sourceParagraph:"स्रोत निर्णय खोलें",
    pioDialogTitle:"PIO सदस्यता",pioDialogText:"PIO सहायता सदस्यता-आधारित होगी। भुगतान और खाता सत्यापन अभी सक्रिय नहीं हैं।",
    understood:"समझ गया",
    candidatePositionsTitle:"मशीन-निकाले अनुच्छेद और तर्क (अभी सत्यापित नहीं)",
    applicantCandidates:"आवेदक/अपीलकर्ता का संभावित तर्क",
    pioCandidates:"PIO/प्रतिवादी का संभावित तर्क",
    findingCandidates:"आयोग/न्यायालय की संभावित टिप्पणी",
    outcomeCandidates:"परिणाम का संभावित संकेत",
    operativeCandidates:"अंतिम आदेश का संभावित अंश",
    issueCandidates:"विवादित मुद्दा",
    sectionCandidates:"धारा-संदर्भ",
    paragraphLabel:"स्रोत पैरा",pageLabel:"PDF पृष्ठ",
    reviewNote:"मशीन सत्यापन स्थिति"
  },
  en: {
    how:"How it works",language:"Language",eyebrow:"Right to Information • Law-based assistance",
    heroTitle:"Understand RTI questions.\nMove forward with the law.",
    heroText:"An independent platform for source-based study of statutes, government orders and judicial decisions.",
    notFiling:"This platform does not automatically file RTI applications or appeals.",free:"FREE",
    applicantTitle:"Applicant assistance",applicantText:"Understand RTI requests, PIO replies, validity of exemptions and first/second appeal options.",
    startApplicant:"Continue as applicant",paid:"SUBSCRIPTION",pioTitle:"PIO assistance",
    pioText:"Review statutory timelines, applicable exemptions, partial disclosure and reasoned replies.",
    startPio:"View PIO assistance",workspaceLabel:"Analysis workspace",close:"Close",
    questionLabel:"What RTI or legal issue do you need help with?",questionPlaceholder:"Describe your question, PIO reply or relevant legal issue...",
    documentsLabel:"File upload (not available yet)",privacyHint:"Your question is searched against verified decisions and machine-extracted candidates. Their verification status is shown separately.",
    submitQuestion:"Get a legal answer",resultTitle:"Legal answer and sources",loading:"Analyzing legal sources and decisions...",completed:"Legal research results are ready.",error:"Research service returned no results: ",answerDisclaimer:"Verified principles and machine-extracted candidates are kept separate. Do not treat a candidate passage as a verified ratio or binding precedent. Check the original source and current law.",candidateEvidenceTitle:"Machine-extracted sources (not yet verified)",checklists:{applicant:["Break the requested information into separate, clear and identifiable record points.","Check the application date, proof of receipt, fee and relevant public authority.","Check every section cited in the PIO reply/refusal and the legal elements required for it.","Consider partial disclosure, inspection of records and available appeal/complaint remedies.","Verify the first-appeal limitation period and the competent First Appellate Authority."],pio:["Document a reasonable records search across relevant branches and record holders.","Distinguish whether information exists, is available, is held by another authority or was destroyed.","If a Section 8/9 exemption is claimed, check each required element and current judicial interpretation.","Check the possibility of severability or partial disclosure under Section 10.","Check the Section 11 third-party process only where legally applicable.","Check statutory timelines for the reply, fee notice and reasoned order."]},methodLabel:"Our method",methodTitle:"Sources first. Conclusions second.",
    step1Title:"Primary sources",step1Text:"Acts, rules, government orders and judicial decisions.",
    step2Title:"Issue-wise review",step2Text:"Assess each legal issue and both parties' arguments separately.",
    step3Title:"Cited response",step3Text:"Show the section, paragraph and source status.",
    disclaimer:"An information assistance platform, not a substitute for a lawyer.",
    decisionTitle:"Decision",authorityLabel:"Court/Commission",sourceParagraph:"Open source decision",
    pioDialogTitle:"PIO subscription",pioDialogText:"PIO assistance will require a subscription. Payments and account verification are not active yet.",
    understood:"Understood",
    candidatePositionsTitle:"Machine-extracted paragraphs and arguments (not yet verified)",
    applicantCandidates:"Applicant/appellant argument candidate",
    pioCandidates:"PIO/respondent argument candidate",
    findingCandidates:"Court/Commission finding candidate",
    outcomeCandidates:"Outcome signal candidate",
    operativeCandidates:"Operative-order passage candidate",
    issueCandidates:"Issue candidate",
    sectionCandidates:"Statutory-section reference",
    paragraphLabel:"Source paragraph",pageLabel:"PDF page",
    reviewNote:"Machine verification status"
  },
  hinglish: {
    how:"Kaise kaam karta hai",language:"Language",eyebrow:"Right to Information • Law-based help",
    heroTitle:"RTI ke sawal samjhein,\nlaw ke basis par aage badhein.",
    heroText:"Acts, government orders aur court decisions ki source-based study ke liye independent platform.",
    notFiling:"Platform RTI application ya appeal automatically file nahi karta.",free:"FREE",
    applicantTitle:"Applicant Help",applicantText:"RTI request, PIO reply, exemption ki validity aur first/second appeal options samjhein.",
    startApplicant:"Applicant ke roop mein aage badhein",paid:"SUBSCRIPTION",pioTitle:"PIO Help",
    pioText:"Legal time limit, exemptions, partial disclosure aur reasoned reply ka analysis karein.",
    startPio:"PIO assistance dekhein",workspaceLabel:"Analysis workspace",close:"Close",
    questionLabel:"Kis RTI ya legal issue par help chahiye?",questionPlaceholder:"Apna sawal, PIO reply ya legal situation likhein...",
    documentsLabel:"File upload (abhi available nahi)",privacyHint:"Aapka sawal verified decisions aur machine-extracted candidates mein search hoga. Dono ki verification status alag dikhai jayegi.",
    submitQuestion:"Legal answer paayein",resultTitle:"Legal answer aur sources",loading:"Legal sources aur decisions ka analysis ho raha hai...",completed:"Legal research result taiyar hai.",error:"Research service se results nahi mile: ",answerDisclaimer:"Verified principles aur machine-extracted candidates alag rakhe gaye hain. Candidate passage ko verified ratio ya binding precedent na maanein. Original source aur current law check karein.",candidateEvidenceTitle:"Machine-extracted sources (abhi verified nahi)",checklists:{applicant:["Maangi gayi information ko alag, clear aur pehchaan-yogya record points mein baantein.","Application date, receipt proof, fee aur relevant public authority check karein.","PIO reply/refusal mein cite har section aur uski legal conditions check karein.","Partial disclosure, records inspection aur available appeal/complaint options dekhein.","First appeal ki limitation aur competent First Appellate Authority verify karein."],pio:["Relevant branches aur record holders mein reasonable record search document karein.","Information available hai, exist nahi karti, doosri authority ke paas hai ya destroy hui—yeh alag karein.","Section 8/9 exemption ho to har legal condition aur current judicial interpretation check karein.","Section 10 ke under severability/partial disclosure ki possibility check karein.","Section 11 third-party process sirf jahan legally applicable ho wahin check karein.","Reply, fee notice aur reasoned order ki statutory timeline check karein."]},methodLabel:"Hamara tareeka",methodTitle:"Pehle source, phir conclusion.",
    step1Title:"Original sources",step1Text:"Acts, rules, government orders aur court decisions.",
    step2Title:"Issue-wise check",step2Text:"Har legal issue aur dono parties ke arguments alag check honge.",
    step3Title:"References ke saath answer",step3Text:"Section, paragraph aur source status clear hoga.",
    disclaimer:"Information assistance platform; lawyer ki service ka replacement nahi.",
    decisionTitle:"Decision",authorityLabel:"Court/Commission",sourceParagraph:"Source decision kholein",
    pioDialogTitle:"PIO subscription",pioDialogText:"PIO help subscription-based hogi. Payment aur account verification abhi active nahi.",
    understood:"Samajh gaya",
    candidatePositionsTitle:"Machine-extracted paragraphs aur arguments (abhi verified nahi)",
    applicantCandidates:"Applicant/appellant ka possible argument",
    pioCandidates:"PIO/respondent ka possible argument",
    findingCandidates:"Commission/court ki possible observation",
    outcomeCandidates:"Outcome ka possible signal",
    operativeCandidates:"Final order ka possible passage",
    issueCandidates:"Issue candidate",
    sectionCandidates:"Section reference",
    paragraphLabel:"Source para",pageLabel:"PDF page",
    reviewNote:"Machine verification status"
  }
};

const languageSelect = document.getElementById("language");
function setLanguage(language) {
  const words = translations[language] || translations.hi;
  document.documentElement.lang = language === "en" ? "en" : "hi";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (words[key]) element.textContent = words[key];
  });
  document.querySelectorAll("[data-placeholder]").forEach((element) => {
    const key = element.dataset.placeholder;
    if (words[key]) element.placeholder = words[key];
  });
  languageSelect.value = language;
  if (latestAnswer) renderLegalAnswer(latestAnswer);
}
languageSelect.addEventListener("change", (event) => setLanguage(event.target.value));

const workspace = document.getElementById("workspace");
document.querySelectorAll("[data-role]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.role === "pio") {
      document.getElementById("pio-dialog").showModal();
      return;
    }
    document.getElementById("workspace-title").textContent = translations[languageSelect.value].applicantTitle;
    workspace.hidden = false;
    workspace.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
document.getElementById("close-workspace").addEventListener("click", () => { workspace.hidden = true; });


let latestAnswer = null;

function renderLegalAnswer(result) {
  const words = translations[languageSelect.value] || translations.hi;
  const output = document.getElementById("analysis-answer");
  output.replaceChildren();
  const addHeading = label => {
    const node = document.createElement("h4");
    node.className = "result-heading";
    node.textContent = label;
    output.append(node);
  };
  const addText = (label, value) => {
    if (value === null || value === undefined || value === "") return;
    const node = document.createElement("p");
    if (label) {
      const strong = document.createElement("strong");
      strong.textContent = label + ": ";
      node.append(strong);
    }
    node.append(document.createTextNode(String(value)));
    output.append(node);
  };
  const addSource = (label, url) => {
    if (!url) return;
    const node = document.createElement("p");
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.textContent = label;
    node.append(anchor);
    output.append(node);
  };

  addText("आपका प्रश्न", result.question);
  addHeading("सीधा जवाब");
  addText("", result.direct_answer || "अभी पर्याप्त स्रोतों के आधार पर निष्कर्ष उपलब्ध नहीं है।");
  if (result.answer_status) addText("स्रोत-आधारित स्थिति", result.answer_status);

  if (result.legal_basis?.length) {
    addHeading("निष्कर्ष का कानूनी आधार");
    result.legal_basis.forEach(item => {
      addText("मुद्दा", item.issue);
      addText("सिद्धांत", item.principle);
      addText("सीमा/दायरा", item.scope);
      if (item.source?.url) addSource(item.source.title || "मूल निर्णय", item.source.url);
    });
  }
  if (result.candidate_evidence?.length) {
    addHeading(words.candidateEvidenceTitle);
    result.candidate_evidence.forEach(item => {
      addText("निर्णय/दस्तावेज़", item.title);
      addText("प्राधिकरण", item.authority);
      addText("निकासी विधि", item.analysis_method);
      addText("निकासी स्थिति", item.analysis_status);
      addText("पाठ निकासी स्थिति", item.extraction_status);
      addSource("मूल स्रोत खोलें", item.canonical_url);
    });
  }
  if (result.candidate_case_positions?.length) {
    addHeading(words.candidatePositionsTitle);
    const groups = [
      ["applicant_argument_candidates", words.applicantCandidates],
      ["pio_argument_candidates", words.pioCandidates],
      ["court_or_commission_finding_candidates", words.findingCandidates],
      ["outcome_candidates", words.outcomeCandidates],
      ["operative_order_candidates", words.operativeCandidates],
      ["issue_candidates", words.issueCandidates],
      ["section_reference_candidates", words.sectionCandidates]
    ];
    result.candidate_case_positions.forEach(item => {
      addText(words.decisionTitle, item.source_title);
      addText(words.authorityLabel, item.authority);
      groups.forEach(([key, label]) => {
        (item[key] || []).forEach(candidate => {
          addText(label, candidate.excerpt);
          addText(words.paragraphLabel, candidate.paragraph_reference);
          addText(words.pageLabel, candidate.page_reference);
          if (candidate.source_url) addSource(words.sourceParagraph, candidate.source_url);
          addText(words.reviewNote, candidate.review_status);
        });
      });
    });
  }
  if (result.case_positions?.length) {
    addHeading("निर्णयों में स्वीकार/अस्वीकार किए गए तर्क");
    result.case_positions.forEach(item => {
      addText("मुद्दा", item.issue);
      addText("आवेदक के स्वीकार तर्क", item.applicant_arguments_accepted?.join(" | "));
      addText("आवेदक के अस्वीकार तर्क", item.applicant_arguments_rejected?.join(" | "));
      addText("PIO के स्वीकार तर्क", item.pio_arguments_accepted?.join(" | "));
      addText("PIO के अस्वीकार तर्क", item.pio_arguments_rejected?.join(" | "));
      addText("परिणाम", item.outcome);
    });
  }
  if (result.conditions_to_check?.length) {
    addHeading("लागू होने की शर्तें");
    result.conditions_to_check.forEach(item => addText("", item));
  }
  if (result.exceptions_to_check?.length) {
    addHeading("कानूनी अपवाद/सीमाएँ");
    result.exceptions_to_check.forEach(item => addText("", item));
  }
  if (result.fact_gaps?.length) {
    addHeading("निष्कर्ष बदल सकने वाला अनुपलब्ध तथ्य");
    result.fact_gaps.forEach(item => addText("", item));
  }
  if (result.next_steps?.length) {
    addHeading("अनुशंसित अगला कदम");
    result.next_steps.forEach(item => addText("", item));
  }
  if (result.citations?.length) {
    addHeading("सत्यापित स्रोत");
    result.citations.forEach(item => addSource(item.title || "मूल निर्णय", item.url));
  }
  if (result.candidate_citations?.length) {
    addHeading("Candidate स्रोत — verified citations नहीं");
    result.candidate_citations.forEach(item => addSource(item.title || "Machine-extracted source", item.url));
  }
  if (result.evidence?.length) {
    addHeading("संबंधित सत्यापित निर्णय");
    result.evidence.forEach(doc => {
      addText("निर्णय", doc.title);
      addText("न्यायालय/प्राधिकरण", doc.authority);
      addText("तारीख", doc.decision_date);
      addText("कानूनी मुद्दा", doc.legal_issue);
      addText("सत्यापित holding", doc.holding);
      addText("संबंधित धाराएँ", doc.cited_sections?.join(", "));
      addSource("मूल स्रोत खोलें", doc.canonical_url);
    });
  } else if (!result.candidate_evidence?.length) {
    addText("सत्यापित निर्णय", "इस प्रश्न से मेल खाता सत्यापित निर्णय नहीं मिला। इसका अर्थ यह नहीं कि आपका दावा गलत है।");
  }
  if (result.verified_principles?.length) {
    addHeading("मानव-सत्यापित वर्तमान कानूनी सिद्धांत");
    result.verified_principles.forEach(principle => {
      addText("मुद्दा", principle.issue);
      addText("सिद्धांत", principle.principle_text);
      addText("शर्तें", principle.conditions?.join(" | "));
      addText("अपवाद", principle.exceptions?.join(" | "));
      addText("आवेदक के स्वीकार तर्क", principle.applicant_arguments_accepted?.join(" | "));
      addText("PIO के स्वीकार तर्क", principle.pio_arguments_accepted?.join(" | "));
      addText("परिणाम", principle.outcome);
      (principle.pinpoint_citations || []).forEach(citation => addText("पैराग्राफ/उद्धरण", JSON.stringify(citation)));
      addSource("सिद्धांत का मूल फैसला खोलें", principle.source_url);
    });
  }
  addText("कानूनी सीमा", result.disclaimer);
  document.getElementById("analysis-result-notice").textContent = words.answerDisclaimer;
  document.getElementById("analysis-result").hidden = false;
}

document.getElementById("analysis-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const words = translations[languageSelect.value] || translations.hi;
  const statusNode = document.getElementById("analysis-status");
  const resultNode = document.getElementById("analysis-result");
  const submitButton = event.currentTarget.querySelector('button[type="submit"]');
  const facts = document.getElementById("question").value.trim();
  const role = document.getElementById("selected-role").value;

  submitButton.disabled = true;
  resultNode.hidden = true;
  latestAnswer = null;
  statusNode.textContent = words.loading;

  try {
    const response = await fetch("/api/v1/research/apply", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify({ role, question: facts, limit: 8 }),
      credentials: "same-origin"
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join("; ")
        : payload.detail;
      throw new Error(detail || "HTTP " + response.status);
    }
    latestAnswer = payload;
    renderLegalAnswer(payload);
    statusNode.textContent = words.completed;
  } catch (error) {
    statusNode.textContent = words.error + error.message;
  } finally {
    submitButton.disabled = false;
  }
});
