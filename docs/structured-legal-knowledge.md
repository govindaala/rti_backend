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

## सुरक्षा नियम
1. Crawler से आया रिकॉर्ड स्वतः verified नहीं होगा।
2. मूल पाठ और metadata-सार अलग रखे जाएँ; API response में raw full text न लौटाएँ।
3. किसी पक्ष की जीत/हार या binding legal principle का निष्कर्ष तभी दें जब अंतिम operative order और citation की मानव समीक्षा हो।
4. वर्तमान वैधता के लिए बाद के निर्णय, appeal/stay/overruling और लागू कानून जाँचें।
5. यह pipeline RAG retrieval की तैयारी है, model fine-tuning या AI training नहीं।
