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
- Worker heartbeat table migration: `supabase/migrations/20261101150000_add_worker_heartbeats.sql`.
- `POST /api/v1/admin/sources` — authenticated और CSRF-protected source queue.
- `POST /api/v1/admin/documents/{document_id}/verify` — reviewer confirmation और कारण सहित document verification.
- `GET /api/v1/admin/documents/ocr-pending?limit=20&offset=0` — authenticated, paginated OCR backlog.
- `POST /api/v1/admin/documents/{document_id}/retry-ocr` — केवल `needs_ocr` documents को authenticated/CSRF-protected retry queue में डालें; verification नहीं करता.
- `POST /api/v1/research/search` — केवल `verified` legal documents में खोज.
- `POST /api/v1/research/apply` — नए प्रश्न पर verified judgments और मानव-सत्यापित वर्तमान ratio लागू करें.
- `POST /api/v1/research/answer` — केवल verified evidence/current ratio पर optional FreeLLMAPI/OpenAI-compatible हिन्दी उत्तर; citations allowlist से validate होते हैं.
- `POST /api/v1/knowledge/principles` — Admin द्वारा ratio/obiter/प्रक्रियात्मक सिद्धांत pending review में दर्ज करें.
- `GET /api/v1/knowledge/principles/pending` — Admin review queue.
- `POST /api/v1/knowledge/principles/{id}/review` — सिद्धांत की वर्तमान/बदली/overruled स्थिति की समीक्षा.
- `GET /api/v1/knowledge/principles/search?query=...` — केवल verified current ratio खोजें.
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
| `DATA_GOV_API_KEY` | data.gov.in की API key; केवल Render/server secret में रखें |
| `DATA_GOV_RESOURCE_IDS` | comma-separated data.gov.in dataset resource IDs |
| `DATA_GOV_API_PAGE_LIMIT` | प्रति API request अधिकतम records; default 100, maximum 1000 |
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `LLM_API_BASE_URL` | वैकल्पिक gateway base URL, जैसे `https://gateway.example/v1` |
| `LLM_API_KEY` | gateway का unified bearer key; केवल Render secret |
| `LLM_MODEL` | gateway में उपलब्ध model ID |
| `LLM_TIMEOUT_SECONDS` | request timeout; default 30 seconds |

`ADMIN_SESSION_SECRET` को `ADMIN_PASS` से अलग रखें। किसी भी secret को GitHub, browser code, README, logs या chat में न डालें। Browser को केवल 8 घंटे की signed `HttpOnly`, `Secure`, `SameSite=Strict` session cookie मिलती है। State-changing admin requests में CSRF token आवश्यक है। पासवर्ड या signing secret बदलने पर पुराने sessions अमान्य हो जाते हैं।

यह implementation अभी single-admin environment credential authentication है; multi-user accounts, granular role/permission management और enterprise identity provider integration अभी शामिल नहीं हैं।

## वैकल्पिक FreeLLMAPI / LLM gateway integration\n\nBackend में OpenAI-compatible `/chat/completions` adapter जोड़ा गया है। FreeLLMAPI को अलग से self-host करके उसके dashboard में provider keys जोड़ें, फिर Render web service में `LLM_API_BASE_URL` (gateway का `/v1` base URL), `LLM_API_KEY` (unified gateway key) और `LLM_MODEL` सेट करें। ये credentials केवल server-side Render environment में रखें; GitHub या browser में नहीं।\n\n`POST /api/v1/research/answer` पहले मौजूदा deterministic engine से verified evidence खोजता है, फिर उन्हीं verified documents और `verified_current` principles को LLM को देता है। Machine-extracted candidates LLM context से बाहर रहते हैं; लौटाए गए citation IDs को backend allowlist से जाँचता है। कोई verified evidence न मिले तो model call नहीं होता। LLM gateway बंद/अनुपलब्ध होने पर मूल `/research/apply` deterministic रूप से उपलब्ध रहता है। बाहरी LLM provider को भेजे गए प्रश्न/स्रोत अंश third-party processing के अधीन होंगे; production उपयोग से पहले PII redaction और provider retention/privacy terms की समीक्षा करें।\n\nFreeLLMAPI खुद RTI backend में embed नहीं होता; यह अलग gateway service है। इस code change से gateway server deploy या provider API keys provision नहीं होतीं।\n\n## Supabase database

Supabase project के private `rti` schema में मुख्य tables:

- `rti.research_sources`
- `rti.crawl_jobs`
- `rti.legal_documents`
- `rti.crawl_job_events`

Schema changes `supabase/migrations/` में version-controlled हैं। OCR states के लिए `supabase/migrations/20261101133000_add_ocr_extraction_state.sql` को connected Supabase project में लागू करना आवश्यक है; GitHub में migration file होने से production database अपने-आप update नहीं होता। `rti` schema को browser के `anon` या `authenticated` roles के लिए expose न करें; backend के server-side database role से ही access दें। RLS enabled रहना चाहिए।

पहले साझा किया गया database password सुरक्षित नहीं माना जाना चाहिए; उसे Supabase में rotate करके ही नई `DATABASE_URL` बनाएं। Production में least-privilege database role और tested backup/restore प्रक्रिया आवश्यक है।

## data.gov.in API integration

Worker में वैकल्पिक JSON API ingestion उपलब्ध है। Render worker के server-side environment में `DATA_GOV_API_KEY` और `DATA_GOV_RESOURCE_IDS` (comma-separated resource IDs) सेट करने पर worker configured resources को queue में डालता है। API key request के समय जोड़ी जाती है; source URL या database record में key नहीं रखी जाती। API results सामान्य extracted documents की तरह `review_required` रहते हैं और स्वतः verified legal material नहीं बनते। API key और resource IDs सेट किए बिना कोई data.gov.in API request नहीं होती।

data.gov.in पर उपलब्ध datasets अलग-अलग हैं; यह integration सभी सरकारी निर्णयों या सभी dataset records की उपलब्धता की गारंटी नहीं देता। Resource ID चुनने से पहले dataset का विषय, publisher, update date और API availability जाँचें।

LiveLaw की वर्तमान Terms of Use सामग्री को सामान्यतः व्यक्तिगत/गैर-व्यावसायिक उपयोग तक सीमित करती हैं। इसलिए LiveLaw लेखों का bulk crawling या पूरा पाठ अपने corpus में copy करना तब तक सक्षम नहीं किया जाएगा जब तक स्पष्ट अनुमति/लाइसेंस न हो। आवश्यकता होने पर केवल citation/link metadata या लिखित अनुमति प्राप्त feed/API को अलग adapter से जोड़ा जा सकता है।

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

`python -m app.worker --check` database schema (worker heartbeat table सहित) और OCR के लिए `eng`/`hin` Tesseract languages की readiness JSON में दिखाता है। Database/schema check fail होने पर exit code non-zero है; OCR unavailable होने पर warning देता है ताकि HTML/text PDF crawling फिर भी चल सके.

`render.yaml` में अलग Render Background Worker परिभाषित है। यह Starter plan पर है और इसका recurring paid compute charge होगा। मौजूदा web service Free plan पर है; idle होने पर sleep करती है और 24×7 worker का विकल्प नहीं है।

**Worker अभी deploy नहीं किया गया है।** Queue में source डालना और उसका वास्तव में लगातार crawl होना अलग बातें हैं। 24×7 crawling के लिए Background Worker deploy, उसके साथ समान `DATABASE_URL` configure, और worker logs/queue processing verify करना जरूरी है। Paid worker provision करने से पहले billing/plan की user approval आवश्यक है।

## संरचित RTI ज्ञान निष्कर्षण (RAG की आधार-परत)

- Crawler के निकाले पाठ से नियम-आधारित प्रारंभिक रिकॉर्ड बनता है: RTI Act के स्पष्ट धारा-संदर्भ, मुद्दा-संकेत, आदेश-संकेत और स्रोत URL।
- `learned_summary` में स्वतंत्र, संक्षिप्त metadata-सार रखा जाता है; यह मूल लेख/निर्णय की नकल या verified legal principle नहीं है। छोटे source excerpts अलग fields में केवल reviewer की जाँच के लिए रहते हैं।
- `/api/v1/research/search` केवल `verified` दस्तावेज़ों को खोजता है और उत्तर में संक्षिप्त सार, मुद्दा/आदेश संकेत, धारा-संदर्भ, स्रोत URL तथा content hash देता है; यह पूरे extracted document को response में नहीं लौटाता।
- यह अभी rule-based extraction + PostgreSQL full-text retrieval है, AI model training/fine-tuning नहीं। बाद में वास्तविक RAG/LLM जोड़ने से पहले source license, PII redaction, citation grounding, hallucination tests और human review की आवश्यकता होगी।
- LiveLaw जैसे गैर-सरकारी प्रकाशक का उपयोग अधिकतम discovery/citation metadata के लिए अलग से किया जा सकता है; उसका पूरा लेख crawler में ingest नहीं किया जाता। निर्णय की पुष्टि प्राथमिक आधिकारिक न्यायालय/आयोग स्रोत से की जानी चाहिए।

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
