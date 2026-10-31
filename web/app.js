// रिपॉजिटरी पथ: rti_backend/web/app.js
"use strict";

// UI में कोई बाहरी AI API नहीं है; विश्लेषण सुविधा backend बनने तक बंद रहेगी।
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
    documentsLabel:"दस्तावेज़ अपलोड (अभी उपलब्ध नहीं)",privacyHint:"आपका प्रश्न backend पर भेजकर केवल नियम-आधारित प्रारंभिक जाँच सूची बनाई जाएगी। यह AI कानूनी राय नहीं है।",
    submitQuestion:"प्रारंभिक जाँच सूची बनाएँ",resultTitle:"प्रारंभिक जाँच सूची",loading:"जाँच सूची तैयार की जा रही है...",completed:"प्रारंभिक जाँच सूची तैयार है।",error:"Backend से जाँच सूची नहीं मिल सकी: ",checklistDisclaimer:"यह नियम-आधारित प्रारंभिक जाँच है, AI कानूनी राय या अंतिम सलाह नहीं। मूल कानून और वर्तमान निर्णयों की अलग से पुष्टि करें।",checklists:{applicant:["माँगी गई सूचना को अलग-अलग, स्पष्ट और पहचान योग्य अभिलेख-बिंदुओं में बाँटें।","आवेदन की तारीख, प्राप्ति का प्रमाण, शुल्क और संबंधित लोक प्राधिकरण जाँचें।","PIO के उत्तर/अस्वीकृति में उद्धृत प्रत्येक धारा और उसके आवश्यक तत्व जाँचें।","आंशिक प्रकटीकरण, अभिलेख निरीक्षण और उपलब्ध अपील/शिकायत उपायों पर विचार करें।","प्रथम अपील की समय-सीमा और सक्षम प्रथम अपीलीय प्राधिकारी की पुष्टि करें."],pio:["संबंधित शाखाओं और अभिलेख-धारकों में उचित रिकॉर्ड खोज का दस्तावेजीकरण करें।","सूचना उपलब्ध है, अस्तित्व में नहीं है, अन्य प्राधिकरण के पास है या नष्ट हुई—स्थिति अलग करें।","धारा 8/9 का कोई अपवाद लागू हो तो उसके प्रत्येक आवश्यक तत्व और वर्तमान न्यायिक व्याख्या जाँचें।","धारा 10 के तहत पृथक्करण/आंशिक प्रकटीकरण की संभावना जाँचें।","धारा 11 की third-party प्रक्रिया केवल जहाँ वैधानिक रूप से लागू हो वहाँ जाँचें।","उत्तर, शुल्क-सूचना और कारणयुक्त आदेश की वैधानिक समय-सीमा जाँचें."]},methodLabel:"हमारा तरीका",methodTitle:"स्रोत पहले, निष्कर्ष बाद में।",
    step1Title:"मूल स्रोत",step1Text:"अधिनियम, नियम, सरकारी आदेश और न्यायिक निर्णय।",
    step2Title:"मुद्दा-वार जाँच",step2Text:"हर कानूनी प्रश्न और दोनों पक्षों के तर्क अलग-अलग।",
    step3Title:"संदर्भ सहित उत्तर",step3Text:"धारा, पैरा और स्रोत की स्थिति स्पष्ट करके।",
    disclaimer:"यह सूचना-सहायक मंच है, वकील की सेवाओं का विकल्प नहीं।",
    pioDialogTitle:"PIO सदस्यता",pioDialogText:"PIO सहायता सदस्यता-आधारित होगी। भुगतान और खाता सत्यापन अभी सक्रिय नहीं हैं।",
    understood:"समझ गया"
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
    documentsLabel:"File upload (not available yet)",privacyHint:"Your question is sent to the backend to create a rules-based preliminary checklist only. This is not an AI legal opinion.",
    submitQuestion:"Create preliminary checklist",resultTitle:"Preliminary checklist",loading:"Preparing the checklist...",completed:"Preliminary checklist is ready.",error:"Could not get the checklist from the backend: ",checklistDisclaimer:"This is a rules-based preliminary checklist, not an AI legal opinion or final advice. Verify the current statute and later judgments separately.",checklists:{applicant:["Break the requested information into separate, clear and identifiable record points.","Check the application date, proof of receipt, fee and relevant public authority.","Check every section cited in the PIO reply/refusal and the legal elements required for it.","Consider partial disclosure, inspection of records and available appeal/complaint remedies.","Verify the first-appeal limitation period and the competent First Appellate Authority."],pio:["Document a reasonable records search across relevant branches and record holders.","Distinguish whether information exists, is available, is held by another authority or was destroyed.","If a Section 8/9 exemption is claimed, check each required element and current judicial interpretation.","Check the possibility of severability or partial disclosure under Section 10.","Check the Section 11 third-party process only where legally applicable.","Check statutory timelines for the reply, fee notice and reasoned order."]},methodLabel:"Our method",methodTitle:"Sources first. Conclusions second.",
    step1Title:"Primary sources",step1Text:"Acts, rules, government orders and judicial decisions.",
    step2Title:"Issue-wise review",step2Text:"Assess each legal issue and both parties' arguments separately.",
    step3Title:"Cited response",step3Text:"Show the section, paragraph and source status.",
    disclaimer:"An information assistance platform, not a substitute for a lawyer.",
    pioDialogTitle:"PIO subscription",pioDialogText:"PIO assistance will require a subscription. Payments and account verification are not active yet.",
    understood:"Understood"
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
    documentsLabel:"File upload (abhi available nahi)",privacyHint:"Aapka sawal backend ko bhejkar sirf rule-based preliminary checklist banegi. Yeh AI legal opinion nahi hai.",
    submitQuestion:"Preliminary checklist banayein",resultTitle:"Preliminary checklist",loading:"Checklist taiyar ho rahi hai...",completed:"Preliminary checklist taiyar hai.",error:"Backend se checklist nahi mil saki: ",checklistDisclaimer:"Yeh rule-based preliminary checklist hai, AI legal opinion ya final advice nahi. Current Act aur baad ke judgments alag se verify karein.",checklists:{applicant:["Maangi gayi information ko alag, clear aur pehchaan-yogya record points mein baantein.","Application date, receipt proof, fee aur relevant public authority check karein.","PIO reply/refusal mein cite har section aur uski legal conditions check karein.","Partial disclosure, records inspection aur available appeal/complaint options dekhein.","First appeal ki limitation aur competent First Appellate Authority verify karein."],pio:["Relevant branches aur record holders mein reasonable record search document karein.","Information available hai, exist nahi karti, doosri authority ke paas hai ya destroy hui—yeh alag karein.","Section 8/9 exemption ho to har legal condition aur current judicial interpretation check karein.","Section 10 ke under severability/partial disclosure ki possibility check karein.","Section 11 third-party process sirf jahan legally applicable ho wahin check karein.","Reply, fee notice aur reasoned order ki statutory timeline check karein."]},methodLabel:"Hamara tareeka",methodTitle:"Pehle source, phir conclusion.",
    step1Title:"Original sources",step1Text:"Acts, rules, government orders aur court decisions.",
    step2Title:"Issue-wise check",step2Text:"Har legal issue aur dono parties ke arguments alag check honge.",
    step3Title:"References ke saath answer",step3Text:"Section, paragraph aur source status clear hoga.",
    disclaimer:"Information assistance platform; lawyer ki service ka replacement nahi.",
    pioDialogTitle:"PIO subscription",pioDialogText:"PIO help subscription-based hogi. Payment aur account verification abhi active nahi.",
    understood:"Samajh gaya"
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
  if (latestChecklist) renderChecklist(latestChecklist);
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


let latestChecklist = null;

function renderChecklist(result) {
  const words = translations[languageSelect.value] || translations.hi;
  const list = document.getElementById("analysis-checklist");
  const translated = words.checklists?.[result.role] || result.checklist;
  list.replaceChildren();
  result.checklist.forEach((item, index) => {
    const entry = document.createElement("li");
    entry.textContent = translated[index] || item;
    list.append(entry);
  });
  document.getElementById("analysis-result-notice").textContent =
    words.checklistDisclaimer;
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
  latestChecklist = null;
  statusNode.textContent = words.loading;

  try {
    const response = await fetch("/api/v1/analysis/checklist", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify({ role, facts }),
      credentials: "same-origin"
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join("; ")
        : payload.detail;
      throw new Error(detail || "HTTP " + response.status);
    }
    latestChecklist = payload;
    renderChecklist(payload);
    statusNode.textContent = words.completed;
  } catch (error) {
    statusNode.textContent = words.error + error.message;
  } finally {
    submitButton.disabled = false;
  }
});
