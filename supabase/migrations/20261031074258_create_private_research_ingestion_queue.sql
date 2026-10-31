-- रिपॉजिटरी पथ: rti_backend/supabase/migrations/20261031074258_create_private_research_ingestion_queue.sql
-- Private research-ingestion schema. No public Data API access.
CREATE SCHEMA IF NOT EXISTS rti;
REVOKE ALL ON SCHEMA rti FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA rti TO postgres, service_role;

CREATE TABLE IF NOT EXISTS rti.research_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    submitted_url text NOT NULL,
    normalized_url text NOT NULL UNIQUE,
    source_label text,
    status text NOT NULL DEFAULT 'queued'
      CHECK (status IN ('queued','discovering','completed','failed','paused')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    last_error_code text
);

CREATE TABLE IF NOT EXISTS rti.crawl_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES rti.research_sources(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'queued'
      CHECK (status IN ('queued','running','completed','failed','cancelled')),
    discovered_count integer NOT NULL DEFAULT 0 CHECK (discovered_count >= 0),
    processed_count integer NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
    failed_count integer NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    current_url text,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    heartbeat_at timestamptz,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    last_error_code text
);

CREATE INDEX IF NOT EXISTS crawl_jobs_status_created_idx
  ON rti.crawl_jobs(status, created_at);

CREATE TABLE IF NOT EXISTS rti.legal_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES rti.research_sources(id) ON DELETE CASCADE,
    job_id uuid NOT NULL REFERENCES rti.crawl_jobs(id) ON DELETE CASCADE,
    canonical_url text NOT NULL UNIQUE,
    title text,
    court_or_authority text,
    decision_date date,
    document_type text NOT NULL DEFAULT 'unknown'
      CHECK (document_type IN ('judgment','order','circular','notification','other','unknown')),
    content_type text,
    extracted_text text,
    content_sha256 text,
    status text NOT NULL DEFAULT 'discovered'
      CHECK (status IN ('discovered','downloading','extracting','extracted','review_required','verified','failed')),
    page_count integer CHECK (page_count IS NULL OR page_count >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    last_error_code text
);

CREATE INDEX IF NOT EXISTS legal_documents_job_status_idx
  ON rti.legal_documents(job_id, status);

CREATE TABLE IF NOT EXISTS rti.crawl_job_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES rti.crawl_jobs(id) ON DELETE CASCADE,
    event_type text NOT NULL,
    message text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS crawl_job_events_job_created_idx
  ON rti.crawl_job_events(job_id, created_at DESC);

ALTER TABLE rti.research_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE rti.crawl_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE rti.legal_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rti.crawl_job_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON ALL TABLES IN SCHEMA rti FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA rti TO postgres, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rti TO postgres, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA rti
  REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA rti
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO postgres, service_role;

