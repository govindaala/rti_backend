-- रिपॉजिटरी पथ: rti_backend/supabase/migrations/20261031100603_remove_duplicate_crawl_event_index.sql
-- पहले से मौजूद crawl_job_events index के साथ duplicate index हटाएँ.
DROP INDEX IF EXISTS rti.idx_rti_crawl_job_events_job_created;
