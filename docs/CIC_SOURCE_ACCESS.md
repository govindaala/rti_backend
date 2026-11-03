<!-- रिपॉजिटरी पथ: rti_backend/docs/CIC_SOURCE_ACCESS.md -->

# केंद्रीय सूचना आयोग (CIC): निर्णय स्रोत और सुरक्षित पहुँच

## आधिकारिक प्रवेश पृष्ठ

- मुख्य वेबसाइट: https://cic.gov.in/
- निर्णय landing page: https://cic.gov.in/decision
- इस landing page पर 10 सितंबर 2016 के बाद के निर्णय और उससे पहले के पुराने निर्णयों के अलग-अलग आधिकारिक पोर्टल लिंक दिए गए हैं।

## वर्तमान स्वचालन सीमा

निर्णय पोर्टल `dsscic.nic.in` पर निर्णय प्रकार, आयुक्त, अपील/शिकायत, फाइल नंबर, पक्षकार/लोक प्राधिकरण और तारीख की खोज के लिए form देता है। पृष्ठ पर CAPTCHA भी मौजूद है। Render के हालिया crawler logs में इस host की `robots.txt` request पर HTTP 403 मिला है।

इसलिए crawler को robots policy अस्वीकार/अस्पष्ट होने पर उस host की सामग्री fetch नहीं करनी चाहिए। CAPTCHA, login, robots policy या अन्य access control को bypass नहीं करना है। HTTP 403 को अनुमति मानकर retry करना भी उचित नहीं है।

## आगे का अनुमत तरीका

1. पहले CIC landing page और उससे उपलब्ध सार्वजनिक metadata को सुरक्षित रूप से पढ़ें।
2. 10 सितंबर 2016 की सीमा को बनाए रखें: नए और पुराने निर्णयों के लिए CIC के अलग-अलग आधिकारिक पोर्टल हैं।
3. निर्णयों की खोज/डाउनलोड तभी automate करें जब आधिकारिक portal robots/access policy इसकी अनुमति दे या CIC कोई documented public API/feed उपलब्ध कराए।
4. CAPTCHA वाले form को automated तरीके से हल न करें। अधिकृत मानव reviewer आधिकारिक portal पर निर्णय खोजकर citation और उपलब्ध metadata दर्ज कर सकता है; इससे automated fetch की अनुमति नहीं मिलती।
5. प्रत्येक वैध रूप से प्राप्त निर्णय को `review_required` में रखें; तारीख, आयोग, केस/अपील संख्या, पक्षकार, source URL और content hash दर्ज करें। मानव सत्यापन के बिना उसे verified legal corpus में न डालें।

## परियोजना की crawl प्राथमिकता

पहला चरण केवल CIC corpus है। योजना 1 नवंबर 2026 से पीछे की ओर 10 सितंबर 2016 तक निर्णय खोजने की है। पुराने निर्णयों का अलग पोर्टल अलग source path है; केवल homepage या सामान्य sitemap crawl को पूर्ण CIC corpus न माना जाए।

Supreme Court, High Courts और State Information Commissions की ingestion CIC चरण के बाद ही शुरू की जाए।
