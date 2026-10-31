-- रिपॉजिटरी पथ: migrations/20261031100544_rti_worker_recovery_and_review_audit.sql
-- RTI Research schema: durable crawler queue, source registry और verified legal corpus.
-- Supabase SQL Editor में एक बार चलाएँ; statements idempotent रखे गए हैं।

CREATE SCHEMA IF NOT EXISTS rti;

CREATE TABLE IF NOT EXISTS rti.research_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    submitted_url text NOT NULL,
    normalized_url text NOT NULL UNIQUE,
    source_label text,
    status text NOT NULL DEFAULT 'queued',
    last_error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rti.crawl_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES rti.research_sources(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'queued',
    current_url text,
    discovered_count integer NOT NULL DEFAULT 0,
    processed_count integer NOT NULL DEFAULT 0,
    failed_count integer NOT NULL DEFAULT 0,
    attempts integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 5,
    available_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    heartbeat_at timestamptz,
    finished_at timestamptz,
    last_error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rti.legal_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES rti.research_sources(id) ON DELETE CASCADE,
    job_id uuid REFERENCES rti.crawl_jobs(id) ON DELETE SET NULL,
    canonical_url text NOT NULL UNIQUE,
    title text,
    court_or_authority text,
    decision_date date,
    document_type text NOT NULL DEFAULT 'unknown',
    content_type text,
    extracted_text text,
    content_sha256 char(64),
    page_count integer,
    status text NOT NULL DEFAULT 'review_required',
    review_note text,
    verified_at timestamptz,
    last_error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rti.crawl_job_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL REFERENCES rti.crawl_jobs(id) ON DELETE CASCADE,
    event_type text NOT NULL,
    message text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Existing deployments को नए worker retry/recovery fields तक सुरक्षित upgrade करें.
ALTER TABLE rti.crawl_jobs
    ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE rti.crawl_jobs
    ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz;
ALTER TABLE rti.crawl_jobs
    ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0;
ALTER TABLE rti.crawl_jobs
    ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 5;
ALTER TABLE rti.crawl_jobs
    ADD COLUMN IF NOT EXISTS last_error_code text;
ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS review_note text;
ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS verified_at timestamptz;
ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS court_or_authority text;
ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS decision_date date;

CREATE INDEX IF NOT EXISTS idx_rti_crawl_jobs_ready
    ON rti.crawl_jobs (available_at, created_at)
    WHERE status = 'queued';
CREATE INDEX IF NOT EXISTS idx_rti_crawl_jobs_stale
    ON rti.crawl_jobs (heartbeat_at)
    WHERE status = 'running';
CREATE INDEX IF NOT EXISTS idx_rti_crawl_jobs_source_status
    ON rti.crawl_jobs (source_id, status);
CREATE INDEX IF NOT EXISTS idx_rti_legal_documents_verified_date
    ON rti.legal_documents (decision_date DESC)
    WHERE status = 'verified';
CREATE INDEX IF NOT EXISTS idx_rti_crawl_job_events_job_created
    ON rti.crawl_job_events (job_id, created_at DESC);
