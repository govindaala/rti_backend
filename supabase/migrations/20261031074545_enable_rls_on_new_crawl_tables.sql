-- रिपॉजिटरी पथ: rti_backend/supabase/migrations/20261031074545_enable_rls_on_new_crawl_tables.sql
ALTER TABLE rti.sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE rti.crawl_events ENABLE ROW LEVEL SECURITY;
