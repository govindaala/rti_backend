# RTI Intelligence Platform — Backend

यह रिपोजिटरी RTI Intelligence Platform के बैकएंड की आधारभूत संरचना है।

## उद्देश्य
- Applicant Intelligence और PIO Intelligence के लिए साझा, सत्यापित कानूनी ज्ञान-संग्रह।
- कानून, आधिकारिक स्रोत और निर्णयों के प्रमाण के साथ विश्लेषण।
- यह प्लेटफ़ॉर्म RTI आवेदन या अपील अपने-आप दाखिल नहीं करेगा।
- उपयोगकर्ता दस्तावेज़ों को साझा ज्ञान-संग्रह में जोड़ने से पहले स्पष्ट सहमति, पहचान हटाना और समीक्षा आवश्यक होगी।

## पहला चरण
FastAPI सेवा, कॉन्फ़िगरेशन, हेल्थ API और स्वचालित परीक्षण।

## स्थानीय रूप से चलाएँ
Python 3.11 या नया संस्करण आवश्यक है।

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

हेल्थ जाँच: `http://127.0.0.1:8000/api/v1/health`
API दस्तावेज़: `http://127.0.0.1:8000/docs`

## सुरक्षा
वास्तविक API keys, पासवर्ड या उपयोगकर्ता दस्तावेज़ GitHub में commit न करें।
## ऑनलाइन डेटाबेस नीति

मुख्य कानूनी डेटा के लिए ऑनलाइन Free Tier database चुना जाएगा। अभी कोई database vendor जोड़ा या configure नहीं किया गया है। चयन से पहले free-tier limits, backup/export, region, security rules और data portability की जाँच होगी।

## बाहरी API निर्भरता नीति

इस backend में किसी बाहरी AI-provider API या third-party AI model को जोड़ना स्वीकार्य नहीं है। ऑनलाइन Free Tier database चुनने के बाद उसके storage connection/SDK का उपयोग केवल डेटा पढ़ने-लिखने के लिए किया जा सकता है; उसे AI inference या बाहरी AI सेवा के रूप में उपयोग नहीं किया जाएगा। कानूनी स्रोतों के लिए सरकारी वेबसाइटों के सार्वजनिक पृष्ठों को अपने लिखे हुए fetcher/parser से पढ़ा जाएगा; किसी vendor search API पर निर्भरता नहीं होगी। AI inference को भी अपने नियंत्रित runtime में चलाने की अलग engineering आवश्यकता है।

## यूजर और Admin UI

- यूजर UI: `/app` — हिन्दी, English और Hinglish; Applicant/PIO role entry।
- Admin UI: `/admin` — केंद्रीय नियंत्रण कक्ष का प्रारंभिक dashboard।
- Static assets इसी FastAPI सेवा से `/assets/` पर serve होते हैं; अलग frontend repository नहीं बनाई गई।
- अभी UI प्रारंभिक है: प्रश्न विश्लेषण API, फाइल अपलोड, login/session, role permissions, सदस्यता और admin operations सक्रिय नहीं हैं।
- Admin UI को वास्तविक authentication और authorization बनने तक सार्वजनिक production में उपयोग नहीं करना है।

## वर्तमान सीमा

Backend में अभी health endpoint, कानूनी केस validation model/API, source-domain review helper और भूमिका-आधारित analysis instruction builder हैं। वास्तविक persistent online database, authentication, crawler, PDF/OCR, legal-content verification, AI model training/inference runtime और production admin APIs अभी बने नहीं हैं। सरकारी domain पहचानना किसी पृष्ठ या निर्णय की सामग्री को सत्यापित करने के बराबर नहीं है।
