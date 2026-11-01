-- Repository path: rti_backend/supabase/migrations/20261101200000_enable_official_discovery_scheduler_extensions.sql
-- Supabase-managed scheduler and asynchronous HTTP request extensions.
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;
