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