-- Repository path: rti_backend/supabase/migrations/20261101150000_add_worker_heartbeats.sql
-- Track actual worker-process liveness separately from per-job heartbeat timestamps.
-- No client-facing policies are created; only trusted server-side database roles should write/read this table.

CREATE TABLE IF NOT EXISTS rti.worker_heartbeats (
    worker_id text PRIMARY KEY,
    hostname text NOT NULL,
    process_id integer NOT NULL CHECK (process_id > 0),
    status text NOT NULL CHECK (status IN ('running', 'stopped')),
    started_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    stopped_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT worker_heartbeats_stopped_state_check
        CHECK ((status = 'running' AND stopped_at IS NULL)
            OR (status = 'stopped' AND stopped_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_rti_worker_heartbeats_status_last_seen
    ON rti.worker_heartbeats (status, last_seen_at DESC);

ALTER TABLE rti.worker_heartbeats ENABLE ROW LEVEL SECURITY;
