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
## Firestore कानूनी केस संग्रह

इस चरण में Firestore repository adapter जोड़ा गया है। यह अभी API से सार्वजनिक रूप से write-enabled नहीं है; authentication और authorization लागू होने से पहले कोई खुला write endpoint नहीं दिया जाएगा।

### आवश्यक सेटिंग

- Google Cloud में Firestore database बनाएँ।
- Runtime को न्यूनतम आवश्यक Firestore permissions वाला service account दें।
- `FIRESTORE_PROJECT_ID` environment variable सेट करें।
- Local development में Application Default Credentials या Firestore Emulator configure करें।
- `.env.example` में केवल project ID का placeholder है; credentials या private keys GitHub पर commit न करें।

### संग्रह संरचना

- Collection: `legal_cases`
- Document ID: `case_id`
- Document fields: forum, case title, decision date, issue-wise findings, citations और verification status।
- Duplicate `case_id` पर मौजूदा रिकॉर्ड overwrite नहीं होगा।

### वर्तमान सीमा

Repository adapter और उसके isolated tests तैयार हैं। वास्तविक Firestore project, credentials, database rules और cloud connection अभी configure नहीं किए गए हैं। सरकारी domain पहचानना स्रोत के पृष्ठ या निर्णय की सामग्री को सत्यापित करने के बराबर नहीं है।
