<!-- Repository path: rti_backend/README.md -->
# RTI Intelligence Platform — Backend

प्रमाण-आधारित RTI कानूनी शोध प्लेटफ़ॉर्म का FastAPI backend.

## स्थायी सिद्धांत

- Applicant और PIO विश्लेषण एक ही verified legal corpus और समान कानूनी स्रोतों पर आधारित होंगे; केवल विश्लेषण का दृष्टिकोण अलग होगा।
- Product runtime में कोई बाहरी AI-provider/model API उपयोग नहीं किया जाता। Supabase PostgreSQL storage है, AI engine नहीं।
- कोई RTI आवेदन/अपील स्वतः दाखिल नहीं होती।
- सरकारी domain होना किसी पेज, आदेश या निर्णय की सामग्री अथवा उसकी वर्तमान कानूनी स्थिति का प्रमाण नहीं है।
- Crawler से प्राप्त नया पाठ `review_required` रहता है। मानव समीक्षा और स्पष्ट कारण दर्ज होने के बाद ही `verified` corpus में जा सकता है।

## Local run

Python 3.11+

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## API और UI

- `GET /api/v1/health` — API process health.
- `GET /api/v1/health/database` — PostgreSQL connection health.
- `POST /api/v1/admin/auth/login` — `ADMIN_ID` / `ADMIN_PASS` से admin login.
- `GET /api/v1/admin/auth/me` — वर्तमान session और CSRF token.
- `POST /api/v1/admin/auth/logout` — CSRF-protected logout.
- `GET /api/v1/admin/dashboard` — authenticated live source/job/document metrics.
- `GET /api/v1/admin/queue-health` — queue backlog, stale jobs और process-level worker heartbeat; worker-heartbeat migration लागू होना आवश्यक है.
- `POST /api/v1/admin/sources` — authenticated और CSRF-protected source queue.
- `POST /api/v1/admin/documents/{document_id}/verify` — reviewer confirmation और कारण सहित document verification.
- `POST /api/v1/admin/documents/{document_id}/retry-ocr` — केवल `needs_ocr` documents को authenticated/CSRF-protected retry queue में डालें; verification नहीं करता.
- `POST /api/v1/research/search` — केवल `verified` legal documents में खोज.
- `POST /api/v1/analysis/checklist` — Applicant/PIO के लिए नियम-आधारित प्रारंभिक checklist.
- `POST /api/v1/drafts/rti` — हिन्दी/English RTI आवेदन मसौदा; कोई auto-submit नहीं.
- `POST /api/v1/drafts/first-appeal` — प्रथम अपील मसौदा; कोई auto-submit नहीं.
- `GET /app` — user interface.
- `GET /admin` — secure login और admin control panel.
- `GET /docs` — API schema.

## Render environment variables

वेब सर्विस या उससे linked Environment Group में ये server-side variables आवश्यक हैं:

| Variable | उपयोग |
|---|---|
| `ADMIN_ID` | Admin login ID |
| `ADMIN_PASS` | Admin password |
| `ADMIN_SESSION_SECRET` | अलग random signing secret; कम से कम 32 bytes |
| `DATABASE_URL` | Supabase PostgreSQL connection string |

`ADMIN_SESSION_SECRET` को `ADMIN_PASS` से अलग रखें। किसी भी secret को GitHub, browser code, README, logs या chat में न डालें। Browser को केवल 8 घंटे की signed `HttpOnly`, `Secure`, `SameSite=Strict` session cookie मिलती है। State-changing admin requests में CSRF token आवश्यक है। पासवर्ड या signing secret बदलने पर पुराने sessions अमान्य हो जाते हैं।

यह implementation अभी single-admin environment credential authentication है; multi-user accounts, granular role/permission management और enterprise identity provider integration अभी शामिल नहीं हैं।

## Supabase database

Supabase project के private `rti` schema में मुख्य tables:

- `rti.research_sources`
- `rti.crawl_jobs`
- `rti.legal_documents`
- `rti.crawl_job_events`

Schema changes `supabase/migrations/` में version-controlled हैं। OCR states के लिए `supabase/migrations/20261101133000_add_ocr_extraction_state.sql` को connected Supabase project में लागू करना आवश्यक है; GitHub में migration file होने से production database अपने-आप update नहीं होता। `rti` schema को browser के `anon` या `authenticated` roles के लिए expose न करें; backend के server-side database role से ही access दें। RLS enabled रहना चाहिए।

पहले साझा किया गया database password सुरक्षित नहीं माना जाना चाहिए; उसे Supabase में rotate करके ही नई `DATABASE_URL` बनाएं। Production में least-privilege database role और tested backup/restore प्रक्रिया आवश्यक है।

## Official-source crawler

- Admin panel में allowlisted HTTPS सरकारी/न्यायिक URL जोड़कर queue किया जा सकता है।
- Source और crawl job PostgreSQL में persist होते हैं।
- Worker `robots.txt` का पालन करता है; redirects, custom ports, URL credentials और non-allowlisted domains अस्वीकार होते हैं।
- HTML/PDF text extraction, content hash और सीमित link discovery उपलब्ध है।
- Scanned/image-only PDFs के लिए Tesseract OCR (`eng+hin`) का bounded attempt उपलब्ध है: अधिकतम 20 पृष्ठ, प्रति पृष्ठ 15-second timeout। OCR engine अनुपलब्ध हो, PDF सीमा से बड़ा हो या extraction विफल हो तो दस्तावेज़ `needs_ocr` रहता है; उसे verified नहीं माना जाता।
- Link discovery अभी सीमित और उसी approved host तक है; यह संपूर्ण web crawler या सभी भारतीय न्यायालयों/आयोगों के लिए पूर्ण adapters नहीं है।
- हर नया दस्तावेज़ `review_required` में रहता है। Reviewer को मूल स्रोत, पूरा निर्णय, तारीख, cited paragraphs, subsequent/overruling history और लागू कानूनी स्थिति जाँचनी चाहिए।
- Login walls, CAPTCHA, paywalls या technical access controls bypass नहीं किए जाते।

### Continuous worker

Local execution:

```bash
python -m app.worker --check
python -m app.worker --once
python -m app.worker --poll
```

`python -m app.worker --check` database schema और OCR के लिए `eng`/`hin` Tesseract languages की readiness JSON में दिखाता है। Database/schema check fail होने पर exit code non-zero है; OCR unavailable होने पर warning देता है ताकि HTML/text PDF crawling फिर भी चल सके.

`render.yaml` में अलग Render Background Worker परिभाषित है। यह Starter plan पर है और इसका recurring paid compute charge होगा। मौजूदा web service Free plan पर है; idle होने पर sleep करती है और 24×7 worker का विकल्प नहीं है।

**Worker अभी deploy नहीं किया गया है।** Queue में source डालना और उसका वास्तव में लगातार crawl होना अलग बातें हैं। 24×7 crawling के लिए Background Worker deploy, उसके साथ समान `DATABASE_URL` configure, और worker logs/queue processing verify करना जरूरी है। Paid worker provision करने से पहले billing/plan की user approval आवश्यक है।

## वर्तमान सीमाएँ — production readiness

- Legal research search verified documents पर PostgreSQL ranked full-text search (`websearch_to_tsquery`/`ts_rank`) और substring fallback का उपयोग करती है; semantic/vector retrieval अभी नहीं है।
- Applicant/PIO analysis अभी नियम-आधारित checklist है, AI judgment analysis या final legal opinion नहीं।
- कोई in-house AI inference/training runtime अभी शामिल नहीं है।
- OCR मौजूद है, लेकिन quality evaluation, OCR retry controls और व्यापक court/tribunal/commission-specific adapters अभी बाकी हैं।
- Multi-user login, granular roles, subscription/payment और user management बाकी हैं।
- Consent, PII redaction, immutable audit trail, backup/restore drills, monitoring/alerts और production security/load testing बाकी हैं।
- Database में वास्तविक कानूनी सामग्री तभी उपलब्ध होगी जब approved sources crawl हों और reviewer documents verify करे। Empty corpus पर legal search परिणाम नहीं दे सकता।

## Tests

```bash
ruff check app tests
node --check web/app.js
node --check web/admin.js
pytest
```
