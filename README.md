# RTI Intelligence Platform — Backend

प्रमाण-आधारित RTI कानूनी शोध प्लेटफ़ॉर्म का FastAPI backend.

## स्थायी सिद्धांत
- Applicant और PIO analysis एक ही सत्यापित legal corpus से facts और law लेते हैं; केवल विश्लेषण का दृष्टिकोण बदलता है।
- कोई बाहरी AI-provider/model API नहीं। Supabase केवल PostgreSQL storage है।
- कोई RTI आवेदन/अपील स्वतः दाखिल नहीं होगी।
- सरकारी domain होना किसी निर्णय के पाठ या कानूनी स्थिति का प्रमाण नहीं; human verification आवश्यक है।
- उपयोगकर्ता दस्तावेज़ साझा corpus में जोड़ने से पहले सहमति, पहचान हटाना और समीक्षा आवश्यक है।

## Local run
Python 3.11+
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Endpoints
- `GET /api/v1/health`
- `GET /api/v1/health/database`
- `GET /api/v1/admin/dashboard` — सार्वजनिक, केवल aggregate/read-only
- `POST /api/v1/admin/sources` — `X-Admin-Token` आवश्यक
- `GET /app` — user interface
- `GET /admin` — password-free read-only dashboard
- `GET /docs` — API schema

## Supabase configuration
Render/server environment में `DATABASE_URL` सेट करें। इसे GitHub, browser, chat या README में न रखें। पहले साझा किया गया database password अब सुरक्षित नहीं माना जाना चाहिए; इस्तेमाल से पहले Supabase में rotate करें। न्यूनतम अधिकार वाला database role उपयोग करें। `rti` schema private रहे और service credentials browser में न जाएँ।

## Source crawler
स्रोत intake केवल allowlisted HTTPS सरकारी/न्यायिक domains स्वीकार करता है। Redirect स्वतः follow नहीं होते; custom ports और URL credentials अस्वीकार हैं। Fetch आकार और timeout सीमित हैं। HTML/PDF से text निकाला जाता है और SHA-256 hash रखा जाता है। निकाला हुआ text `review_required` स्थिति में रहता है—स्वतः verified नहीं होता।

Queue worker one-shot है:
```bash
python -m app.worker --once
python -m app.worker --drain
```
Render Free web service अपने-आप लगातार worker नहीं चलाती और idle होने पर sleep करती है। इसीलिए queue intake और worker execution अलग हैं। निरंतर background processing के लिए अलग worker/cron runtime और बजट/hosting निर्णय चाहिए।

## Admin security
Dashboard बिना password के केवल aggregate counts दिखाता है। Source submission और अन्य privileged actions के लिए `ADMIN_API_TOKEN` server-side environment variable आवश्यक है। Token को browser code या repository में न रखें।

## परीक्षण
```bash
ruff check app tests
pytest
```

## अभी क्या शामिल नहीं है
पूर्ण login/session/role system, user/subscription management, legal decision verification workflow, OCR for scanned PDFs, multi-page website crawling/link discovery, semantic search/index, indigenous AI inference/training runtime, full audit/consent system, backups/restore drills और production worker orchestration अभी अलग engineering phases हैं। इनका झूठा दावा नहीं किया जाता।
