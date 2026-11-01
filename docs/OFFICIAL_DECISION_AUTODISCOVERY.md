# Repository path: rti_backend/docs/OFFICIAL_DECISION_AUTODISCOVERY.md

# Official decision discovery and analysis rollout

## Scheduled discovery

The protected backend endpoint is called three times daily by Supabase Cron: 09:00, 17:00, and 01:00 India time (UTC cron `30 3,11,19 * * *`). Each call processes at most three jobs. It seeds only the configured official-source catalogue and skips creating another source-root job if a queued/running job exists or the last successful source-root job is less than 20 hours old. The configured Render token and Supabase Vault secret must match; neither secret belongs in GitHub.

## Honest analysis status

The local analyzer is intentionally extractive. It stores quoted text, candidate issue/operative language, and RTI Act section citations only when nearby source text explicitly names the Act. Its status is `human_review_required`; it does not claim a judgment was legally understood or verified by a generative model. Excerpts retain the original source URL.

A generative model is not configured because the project currently avoids external AI-provider APIs and the free Render web instance is not a reliable host for a capable legal LLM. Do not label a decision “AI analyzed” unless a locally hosted open-source inference service is configured, its outputs are source-grounded, and tests cover hallucinations/citations.

## Deployment

Apply migrations in order and verify schema before deploying code that queries the new columns. Confirm the daily scheduler with Supabase Cron job history and Render logs. The daily counts are based on India Standard Time. The crawler respects the existing official-domain and robots checks; no source is automatically marked legally verified.
