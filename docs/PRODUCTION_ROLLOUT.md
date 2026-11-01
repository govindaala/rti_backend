# Production rollout checklist

This runbook separates GitHub readiness from production database and Render readiness.
A merged pull request does not prove that the database migrations are applied or that
the background worker is running.

## 1. Pre-deployment safety

- Confirm the intended GitHub commit is on `main` and its required CI checks pass.
- Confirm a current Supabase backup/restore point exists and that restore access is available.
- Confirm the production `DATABASE_URL` points to the intended Supabase project.
- Never put database URLs, passwords, admin credentials, or signing secrets in this
  repository, an issue, a pull request, logs, or browser code.
- The worker is a separate Render Background Worker. The Blueprint in `render.yaml`
  uses the paid Starter plan; review the current Render price and approve the recurring
  charge before creating or enabling it.

## 2. Supabase schema rollout

The following migrations are present on GitHub `main`. GitHub files do not apply
themselves to the connected database.

Apply them in timestamp order using the project's approved Supabase migration process:

1. `20261101120000_add_verified_legal_search_index.sql`
   - Adds the GIN full-text index for verified legal documents.
   - Does not change document verification state.
2. `20261101133000_add_ocr_extraction_state.sql`
   - Adds `extraction_status` and `ocr_required` to `rti.legal_documents`.
   - Adds the extraction-state constraint and partial OCR backlog index.
   - Existing rows receive `legacy_unknown`; none are auto-verified.
3. `20261101150000_add_worker_heartbeats.sql`
   - Creates `rti.worker_heartbeats`.
   - Enables RLS and revokes access from `PUBLIC`, `anon`, and `authenticated`.
   - Grants the required table operations to trusted server-side roles only.

After applying, verify the migration history and inspect the schema. Confirm that
`rti.legal_documents.extraction_status`, `rti.legal_documents.ocr_required`, and
`rti.worker_heartbeats` exist, and that RLS is enabled on the heartbeat table.
Do not weaken RLS or expose the private `rti` schema to browser roles to make the
worker connect. If any migration fails, stop and inspect the database state before
retrying; do not blindly rerun or manually mark a migration as applied.

## 3. Render worker configuration

Before provisioning the worker, verify:

- The worker service uses this repository, branch `main`, and the intended region.
- `DATABASE_URL` is configured as a secret environment variable and points to the
  same production database used by the backend.
- The build installs the required Tesseract packages and Python dependencies.
- The start command remains:
  `python -m app.worker --check && python -m app.worker --poll`
- The worker preflight succeeds. A failed database/schema check must block polling.
- OCR language readiness is reviewed separately; an OCR warning does not mean that
  ordinary HTML/text crawling is unavailable.

The worker has recurring paid compute cost. Do not provision it without explicit
billing approval. The existing web service is not a substitute for the worker.

## 4. Post-deployment acceptance checks

Run these checks after the database migrations and worker deployment:

1. Backend `GET /api/v1/health` returns healthy.
2. Backend `GET /api/v1/health/database` confirms database connectivity.
3. Anonymous `GET /api/v1/admin/queue-health` is rejected.
4. Authenticated `GET /api/v1/admin/queue-health` returns queue and heartbeat data.
5. Worker logs show a successful preflight and continuous polling without schema errors.
6. A test source on an approved domain can be queued from the admin panel.
7. The worker claims that job; database job events and worker heartbeat timestamps
   advance as expected.
8. The resulting document remains `review_required` or `needs_ocr` as appropriate.
   It must not become `verified` without an authorized human review.
9. Stop/restart the worker in a controlled test and confirm heartbeat state and stale
   job recovery behave as expected.

Record the deployed commit SHA, migration versions, Render service status, and test
results. Only describe crawling as live after the worker is observed processing a
queued job against the intended production database.

## 5. Current known boundary

This checklist does not apply database migrations, create Render services, approve
billing, add source URLs, or verify legal documents. Those are separate production
actions and require the appropriate authorization and verification.
