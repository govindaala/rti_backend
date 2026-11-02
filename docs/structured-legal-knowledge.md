<!-- Repository path: rti_backend/docs/structured-legal-knowledge.md -->
# संरचित RTI कानूनी ज्ञान

## लक्ष्य
LiveLaw जैसे गैर-सरकारी प्रकाशकों से पूरे लेख की प्रतिलिपि नहीं बनानी है। जहाँ अनुमति/शर्तें अनुमति दें, वहाँ केवल खोज/संदर्भ metadata और canonical link का उपयोग करें; कानूनी निष्कर्ष प्राथमिक आधिकारिक न्यायालय/आयोग स्रोत से सत्यापित करें।

## रिकॉर्ड संरचना
- स्रोत का शीर्षक, URL, न्यायालय/आयोग, निर्णय तारीख और केस नंबर
- RTI Act की स्पष्ट रूप से संदर्भित धाराएँ
- मुद्दे का संक्षिप्त संकेत
- आदेश/निष्कर्ष का संक्षिप्त संकेत
- स्वतंत्र metadata-सार
- source hash, extraction method, review status और reviewer note

## नया verified-knowledge application endpoint
- `POST /api/v1/research/apply` नया प्रश्न लेकर केवल `status='verified'` legal documents खोजता है।
- Hindi/English प्रश्नों से stop words हटाकर सीमित OR-term retrieval किया जाता है, ताकि लंबे प्राकृतिक भाषा प्रश्नों में एक-एक शब्द के आधार पर प्रासंगिक उम्मीदवार मिल सकें।
- प्रत्येक उम्मीदवार के साथ मूल canonical URL, document ID, content hash, issue, holding, RTI sections और मिले हुए शब्द लौटते हैं।
- `strong_keyword_overlap` / `partial_keyword_overlap` केवल lexical overlap labels हैं; ये AI confidence, कानूनी समानता या binding precedent का दावा नहीं हैं।
- Applicant, PIO और neutral दृष्टिकोण के लिए अलग जाँच-सूचियाँ मिलती हैं, लेकिन सभी के लिए एक ही verified corpus उपयोग होता है।
- निर्णय का operative order, pinpoint paragraphs, तथ्यात्मक अंतर, बाद के निर्णय, stay/appeal और वर्तमान कानून की जाँच के बिना कोई अंतिम कानूनी निष्कर्ष नहीं निकाला जाता।

## सुरक्षा नियम
1. Crawler से आया रिकॉर्ड स्वतः verified नहीं होगा।
2. मूल पाठ और metadata-सार अलग रखे जाएँ; API response में raw full text न लौटाएँ।
3. किसी पक्ष की जीत/हार या binding legal principle का निष्कर्ष तभी दें जब अंतिम operative order और citation की मानव समीक्षा हो।
4. वर्तमान वैधता के लिए बाद के निर्णय, appeal/stay/overruling और लागू कानून जाँचें।
5. मौजूदा endpoint नियम-आधारित retrieval/application है; यह generative AI, model training या स्वतः विकसित होती AI समझ नहीं है।
6. वास्तविक generative AI जोड़ने के लिए अलग model runtime, evaluation corpus, prompt-injection isolation, PII controls, citation grounding और मानव समीक्षा की आवश्यकता होगी।
