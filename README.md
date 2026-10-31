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

## Live endpoints
- `GET /api/v1/health`
- `GET /api/v1/health/database`
- `POST /api/v1/admin/auth/login` — `ADMIN_ID` / `ADMIN_PASS` से secure admin login
- `GET /api/v1/admin/auth/me` — current admin session और CSRF token
- `POST /api/v1/admin/auth/logout` — CSRF-protected logout
- `GET /api/v1/admin/dashboard` — authenticated live metrics और crawl activity
- `POST /api/v1/admin/sources` — authenticated + CSRF-protected source queue
- `POST /api/v1/research/search` — केवल `verified` कानूनी दस्तावेज़ों में खोज
- `POST /api/v1/analysis/checklist` — Applicant/PIO के लिए नियम-आधारित प्रारंभिक checklist
- `POST /api/v1/drafts/rti` — हिन्दी/English RTI आवेदन मसौदा; कोई auto-submit नहीं
- `POST /api/v1/drafts/first-appeal` — धारा 19(1) के अंतर्गत प्रथम अपील मसौदा; कोई auto-submit नहीं
- `GET /app` — user interface
- `GET /admin` — secure login screen और authenticated live operations dashboard
- `GET /docs` — API schema

## Supabase configuration
Render/server environment में `DATABASE_URL` सेट करें। इसे GitHub, browser, chat या README में न रखें। पहले साझा किया गया database password अब सुरक्षित नहीं माना जाना चाहिए; इस्तेमाल से पहले Supabase में rotate करें। न्यूनतम अधिकार वाला database role उपयोग करें। `rti` schema private रहे और service credentials browser में न जाएँ।

मौजूदा Supabase project में `rti.research_sources`, `rti.crawl_jobs`, `rti.legal_documents` और crawl event tables मौजूद हैं; worker इन्हीं tables को durable queue और document store की तरह उपयोग करता है। Recovery/review fields और queue indexes अब version-controlled Supabase migrations में हैं।

## Database migrations

Supabase schema changes are version-controlled under `supabase/migrations/`.
The recovery/review migration was applied to the connected Supabase project on
2026-10-31 (migration `20261031100544`), followed by duplicate-index cleanup
(`20261031100603`). It adds the durable queue availability timestamp, legal
review evidence fields, and queue/recovery indexes without deleting existing data.

For another environment, link the Supabase CLI to that project and run:

```bash
supabase link --project-ref <project-ref>
supabase db push
```

The `rti` schema is private to the server-side database role. Do not grant
`anon` or `authenticated` access to it; the connected project currently
denies those roles schema usage and table access. RLS remains enabled as
defense in depth.

The first historical migration (`20261031061604`) drops a set of legacy `public`
objects. It is retained to match the already-applied project history; review that
file before applying the complete migration chain to any other existing project.

## Continuous official-source crawler
- Admin में allowlisted HTTPS सरकारी/न्यायिक URL डालें और server-side `ADMIN_API_TOKEN` से approve करें।
- Source और job PostgreSQL में persist होते हैं; browser बंद होने पर भी queue सुरक्षित रहती है।
- Worker queue से jobs claim करता है, `robots.txt` का पालन करता है, redirects/custom ports/credentials अस्वीकार करता है और केवल उसी host के legal-path/PDF links discover करता है।
- Per page अधिकतम 25 candidate links और प्रति crawl cycle प्रति source अधिकतम 250 jobs की सीमा है; fetch timeout और byte size सीमित हैं।
- PDF/HTML text, title, source URL और SHA-256 hash database में सुरक्षित होते हैं। Document type केवल preliminary URL/title classification है।
- हर नया दस्तावेज़ `review_required` में रहता है। यह स्वतः verified नहीं होता और legal research API में तब तक उपलब्ध नहीं होगा जब तक authorized reviewer उसे verify न करे।
- Login walls, CAPTCHA, robots disallow, paywalls या technical access controls को bypass नहीं किया जाता। External links और non-allowlisted domains crawl नहीं होते।

### Continuous worker
Local one-shot:
```bash
python -m app.worker --once
```
Continuous polling:
```bash
python -m app.worker --poll
```
Worker SIGTERM/SIGINT पर नया job लेना रोकता है और चल रहा job पूरा होने के बाद बंद होता है।

### Render deployment requirement
`render.yaml` में अलग Render Background Worker परिभाषित है। इसे deploy करने पर Render Starter compute plan वाला अलग worker resource बनेगा और recurring paid compute charge लगेगा। मौजूदा account में backend web service Free plan पर है; वह idle होने पर sleep करती है और उसे 24×7 worker नहीं माना जा सकता। Render की service-type documentation के अनुसार always-on queue consumer के लिए Background Worker उपयुक्त है। Worker के लिए `DATABASE_URL` और web service के लिए `DATABASE_URL` तथा `ADMIN_API_TOKEN` configure करें। Secrets केवल Render Environment में रखें।

**अभी worker deployed नहीं है।** Blueprint को GitHub में merge/push और Render में sync/deploy करने के बाद ही 24×7 execution शुरू होगा। इस PR को merge करना या paid service create करना अपने-आप नहीं किया गया है।

## Admin security
Dashboard बिना token के केवल public aggregate आँकड़े और public document metadata दिखाता है। Source submission के लिए `ADMIN_API_TOKEN` आवश्यक है। Token केवल request header में भेजा जाता है, browser storage में save नहीं होता। Production में HTTPS और मजबूत random token अनिवार्य हैं।

## परीक्षण
```bash
ruff check app tests
pytest
```

## शोध और ड्राफ्ट सुविधाएँ
- Research API केवल `rti.legal_documents.status = 'verified'` वाले दस्तावेज़ों को लौटाती है; pending/review_required crawler output कभी कानूनी प्रमाण के रूप में नहीं दिखता। अभी खोज exact phrase substring आधारित है, semantic/vector search नहीं।
- Analysis checklist Applicant और PIO के लिए अलग जाँच-बिंदु देती है, पर यह AI inference या अंतिम कानूनी राय नहीं है।
- `/app` में Applicant form अब `/api/v1/analysis/checklist` से जुड़ा है और checklist हिन्दी, English तथा Hinglish में दिखती है। यह नियम-आधारित checklist है, AI judgment analysis नहीं। File upload बंद है; PIO subscription/payment और login अभी सक्रिय नहीं हैं।
- RTI draft API हिन्दी/English मसौदा बनाती है। मसौदा database में save या किसी सरकारी portal पर submit नहीं होता। उपयोगकर्ता को लागू केंद्र/राज्य नियम, शुल्क और सही प्राधिकरण जाँचना होगा।

## अभी शेष प्रमुख कार्य
पूर्ण authentication/session/role system, audited legal verification/review UI, OCR for scanned PDFs, richer court/tribunal discovery adapters, semantic/vector search, in-house AI inference and citation-grounded judgment analysis, consent/privacy workflow, immutable audit log, backups/restore drills, monitoring/alerts, and production load/security testing.


## Admin login configuration (Render)

Set these server-side variables on the **web service** or on an Environment Group linked to it:

- `ADMIN_ID`: administrator login ID.
- `ADMIN_PASS`: administrator password (keep secret; never put it in GitHub or chat).
- `ADMIN_SESSION_SECRET`: independent random signing secret, at least 32 bytes. Generate it in a password manager or secure random generator; do not reuse the admin password.

The browser receives only an 8-hour, signed, `HttpOnly`, `Secure`, `SameSite=Strict` session cookie. State-changing admin APIs also require the session CSRF token. The old `ADMIN_API_TOKEN` header is no longer used by the admin UI.

After deployment, open `/admin`, sign in, and confirm the dashboard reports the real database status. A successful login does not mean the crawler is running: the worker and database must be provisioned and independently checked. The free Render web service may sleep when idle.
