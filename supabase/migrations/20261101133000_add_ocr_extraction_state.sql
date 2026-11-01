-- रिपॉजिटरी पथ: rti_backend/supabase/migrations/20261101133000_add_ocr_extraction_state.sql
-- Track text extraction separately from human legal verification.
-- Existing documents remain human-review controlled; no row is auto-verified.

ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS extraction_status text NOT NULL DEFAULT 'legacy_unknown';

ALTER TABLE rti.legal_documents
    ADD COLUMN IF NOT EXISTS ocr_required boolean NOT NULL DEFAULT false;

-- Preserve explicit states for all newly processed records while retaining a safe
-- legacy marker for records collected before extraction-state tracking existed.
ALTER TABLE rti.legal_documents
    DROP CONSTRAINT IF EXISTS legal_documents_extraction_status_check;

ALTER TABLE rti.legal_documents
    ADD CONSTRAINT legal_documents_extraction_status_check
    CHECK (extraction_status IN ('legacy_unknown', 'extracted', 'extracted_ocr', 'needs_ocr', 'empty_text'));

CREATE INDEX IF NOT EXISTS idx_rti_legal_documents_needs_ocr
    ON rti.legal_documents (updated_at)
    WHERE ocr_required = true AND status = 'needs_ocr';
