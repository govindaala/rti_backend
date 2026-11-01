-- Repository path: rti_backend/supabase/migrations/20261101180000_add_official_decision_metadata.sql
-- Metadata for source-attributed decisions; no automatic legal verification.
ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS decision_date date,
    ADD COLUMN IF NOT EXISTS court_name text,
    ADD COLUMN IF NOT EXISTS case_number text,
    ADD COLUMN IF NOT EXISTS read_at timestamptz,
    ADD COLUMN IF NOT EXISTS analysis_status text NOT NULL DEFAULT 'not_started',
    ADD COLUMN IF NOT EXISTS learned_summary text,
    ADD COLUMN IF NOT EXISTS legal_issue text,
    ADD COLUMN IF NOT EXISTS holding text;
ALTER TABLE rti.legal_documents DROP CONSTRAINT IF EXISTS legal_documents_analysis_status_check;
ALTER TABLE rti.legal_documents ADD CONSTRAINT legal_documents_analysis_status_check
    CHECK (analysis_status IN ('not_started','pending_ai','analyzed','text_unavailable','ai_not_configured','analysis_failed','human_review_required'));
CREATE INDEX IF NOT EXISTS idx_rti_legal_documents_decision_date ON rti.legal_documents (decision_date DESC NULLS LAST, read_at DESC);
CREATE INDEX IF NOT EXISTS idx_rti_legal_documents_analysis_status ON rti.legal_documents (analysis_status, read_at DESC);
