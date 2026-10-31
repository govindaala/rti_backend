// रिपॉजिटरी पथ: rti_backend/web/app.js
"use strict";

// UI में केवल अपने backend endpoints को कॉल करें; किसी AI vendor API का उपयोग नहीं।
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
    documentsLabel:"संबंधित दस्तावेज़ (वैकल्पिक)",privacyHint:"संवेदनशील निजी जानकारी हटाकर ही दस्तावेज़ दें। अभी फाइल अपलोड सुविधा सक्रिय नहीं है।",
    submitQuestion:"विश्लेषण अनुरोध भेजें",methodLabel:"हमारा तरीका",methodTitle:"स्रोत पहले, निष्कर्ष बाद में।",
    step1Title:"मूल स्रोत",step1Text:"अधिनियम, नियम, सरकारी आदेश और न्यायिक निर्णय।",
    step2Title:"मुद्दा-वार जाँच",step2Text:"हर कानूनी प्रश्न और दोनों पक्षों के तर्क अलग-अलग।",
    step3Title:"संदर्भ सहित उत्तर",step3Text:"धारा, पैरा और स्रोत की स्थिति स्पष्ट करके।",
    disclaimer:"यह सूचना-सहायक मंच है, वकील की सेवाओं का विकल्प नहीं।",
    pioDialogTitle:"PIO सदस्यता",pioDialogText:"PIO सहायता सदस्यता-आधारित होगी। भुगतान और खाता सत्यापन अभी सक्रिय नहीं हैं।",
    understood:"समझ गया",notReady:"विश्लेषण API अभी तैयार नहीं है। आपका प्रश्न सर्वर पर नहीं भेजा गया है।"
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
    documentsLabel:"Related documents (optional)",privacyHint:"Remove sensitive personal information before sharing. File upload is not active yet.",
    submitQuestion:"Send analysis request",methodLabel:"Our method",methodTitle:"Sources first. Conclusions second.",
    step1Title:"Primary sources",step1Text:"Acts, rules, government orders and judicial decisions.",
    step2Title:"Issue-wise review",step2Text:"Assess each legal issue and both parties' arguments separately.",
    step3Title:"Cited response",step3Text:"Show the section, paragraph and source status.",
    disclaimer:"An information assistance platform, not a substitute for a lawyer.",
    pioDialogTitle:"PIO subscription",pioDialogText:"PIO assistance will require a subscription. Payments and account verification are not active yet.",
    understood:"Understood",notReady:"The analysis API is not ready yet. Your question has not been sent to the server."
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
    documentsLabel:"Related documents (optional)",privacyHint:"Sensitive personal details hata kar hi document dein. File upload abhi active nahi hai.",
    submitQuestion:"Analysis request bhejein",methodLabel:"Hamara tareeka",methodTitle:"Pehle source, phir conclusion.",
    step1Title:"Original sources",step1Text:"Acts, rules, government orders aur court decisions.",
    step2Title:"Issue-wise check",step2Text:"Har legal issue aur dono parties ke arguments alag check honge.",
    step3Title:"References ke saath answer",step3Text:"Section, paragraph aur source status clear hoga.",
    disclaimer:"Information assistance platform; lawyer ki service ka replacement nahi.",
    pioDialogTitle:"PIO subscription",pioDialogText:"PIO help subscription-based hogi. Payment aur account verification abhi active nahi.",
    understood:"Samajh gaya",notReady:"Analysis API abhi ready nahi hai. Aapka sawal server par nahi bheja gaya."
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
}
languageSelect.addEventListener("change", (event) => setLanguage(event.target.value));

const workspace = document.getElementById("workspace");
const status = document.getElementById("analysis-status");
document.querySelectorAll("[data-role]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.role === "pio") {
      document.getElementById("pio-dialog").showModal();
      return;
    }
    document.getElementById("selected-role").value = "applicant";
    document.getElementById("workspace-title").textContent = translations[languageSelect.value].applicantTitle;
    workspace.hidden = false;
    workspace.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
document.getElementById("close-workspace").addEventListener("click", () => { workspace.hidden = true; });
document.getElementById("analysis-form").addEventListener("submit", (event) => {
  event.preventDefault();
  // अधूरा backend देखकर सफल विश्लेषण का झूठा दावा न करें और निजी डेटा न भेजें।
  status.textContent = translations[languageSelect.value].notReady;
});
