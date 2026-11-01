-- Repository path: rti_backend/supabase/migrations/20261101190000_add_extractive_legal_analysis.sql
-- Store source-grounded extracts without implying that a generative model or human reviewer verified them.
ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS cited_sections text[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS key_paragraphs jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS analysis_method text,
    ADD COLUMN IF NOT EXISTS analyzed_at timestamptz;
CREATE INDEX IF NOT EXISTS idx_rti_legal_documents_cited_sections
    ON rti.legal_documents USING GIN (cited_sections);
