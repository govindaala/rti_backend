# Repository path: rti_backend/docs/OFFICIAL_DECISION_AUTODISCOVERY.md

Official decision discovery rollout notes.

Metadata extraction is heuristic, not legal verification. The current backend has no configured LLM inference provider; AI analysis must remain pending until a real provider and citation-grounded output are implemented.

For scheduling, set OFFICIAL_DISCOVERY_TOKEN only in the Render environment and Supabase Vault. Schedule a daily POST to the protected scheduler endpoint through Supabase Cron. Do not put tokens in Git. Apply migrations only after a database backup and review. This is a bounded batch, not a 24x7 worker.
