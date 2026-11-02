-- Repository path: rti_backend/supabase/migrations/20261102050508_add_legal_principle_review_audit.sql
-- Preserve each reviewer decision; updates and audit insert share one transaction.
CREATE TABLE IF NOT EXISTS rti.legal_principle_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    principle_id uuid NOT NULL REFERENCES rti.legal_principles(id) ON DELETE RESTRICT,
    previous_status text NOT NULL,
    new_status text NOT NULL CHECK (new_status IN (
      'pending_review', 'verified_current', 'needs_subsequent_review',
      'distinguished', 'overruled', 'superseded', 'rejected'
    )),
    reviewer text NOT NULL,
    reviewer_note text NOT NULL CHECK (length(btrim(reviewer_note)) >= 20),
    superseded_by_document_id uuid REFERENCES rti.legal_documents(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_legal_principle_reviews_history
    ON rti.legal_principle_reviews (principle_id, created_at DESC);
ALTER TABLE rti.legal_principle_reviews ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE rti.legal_principle_reviews FROM anon, authenticated;
