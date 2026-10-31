-- रिपॉजिटरी पथ: rti_backend/supabase/migrations/20261031074314_create_private_rti_crawl_foundation.sql

create schema if not exists rti;
revoke all on schema rti from public, anon, authenticated;
grant usage on schema rti to service_role;
grant select, insert, update, delete on all tables in schema rti to service_role;
alter default privileges in schema rti grant select, insert, update, delete on tables to service_role;

create table if not exists rti.sources (
  id uuid primary key default gen_random_uuid(),
  submitted_url text not null,
  canonical_host text not null,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','paused')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_error text,
  constraint sources_url_length check (length(submitted_url) between 8 and 2048)
);

create table if not exists rti.crawl_jobs (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references rti.sources(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','paused')),
  discovered_count integer not null default 0 check (discovered_count >= 0),
  processed_count integer not null default 0 check (processed_count >= 0),
  failed_count integer not null default 0 check (failed_count >= 0),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  max_pages integer not null default 500 check (max_pages between 1 and 5000),
  started_at timestamptz,
  finished_at timestamptz,
  heartbeat_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists crawl_jobs_status_created_idx on rti.crawl_jobs(status, created_at);
create index if not exists sources_status_created_idx on rti.sources(status, created_at);

create table if not exists rti.legal_documents (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references rti.sources(id) on delete cascade,
  job_id uuid not null references rti.crawl_jobs(id) on delete cascade,
  document_url text not null,
  title text,
  document_type text not null default 'unknown' check (document_type in ('judgment','order','cause_list','other','unknown')),
  status text not null default 'discovered' check (status in ('discovered','queued','downloading','extracted','needs_review','verified','failed','duplicate')),
  content_type text,
  content_sha256 text,
  extracted_text text,
  page_count integer,
  error_message text,
  discovered_at timestamptz not null default now(),
  processed_at timestamptz,
  unique(job_id, document_url)
);

create index if not exists legal_documents_job_status_idx on rti.legal_documents(job_id, status);
create index if not exists legal_documents_source_idx on rti.legal_documents(source_id);

create table if not exists rti.crawl_events (
  id bigserial primary key,
  job_id uuid not null references rti.crawl_jobs(id) on delete cascade,
  event_type text not null,
  message text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists crawl_events_job_created_idx on rti.crawl_events(job_id, created_at);

