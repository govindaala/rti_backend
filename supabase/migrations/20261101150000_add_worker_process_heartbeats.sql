-- रिपॉजिटरी पथ: rti_backend/supabase/migrations/20261101150000_add_worker_process_heartbeats.sql
-- Process-level heartbeat is distinct from individual crawl-job heartbeats.
CREATE TABLE IF NOT EXISTS rti.worker_heartbeats (
    worker_id text PRIMARY KEY,
    hostname text NOT NULL,
    process_id integer NOT NULL,
    status text NOT NULL CHECK (status IN ('running', 'stopped')),
    started_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    stopped_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rti_worker_heartbeats_running_seen
    ON rti.worker_heartbeats (last_seen_at DESC)
    WHERE status = 'running';

REVOKE ALL ON TABLE rti.worker_heartbeats FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE rti.worker_heartbeats TO service_role;
