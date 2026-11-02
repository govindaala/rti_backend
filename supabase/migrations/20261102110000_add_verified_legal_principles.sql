-- Repository path: rti_backend/supabase/migrations/20261102110000_add_verified_legal_principles.sql
-- Human-reviewed legal principles are stored separately from crawler extracts.
CREATE TABLE IF NOT EXISTS rti.legal_principles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES rti.legal_documents(id) ON DELETE RESTRICT,
    issue text NOT NULL CHECK (length(btrim(issue)) >= 8),
    principle_type text NOT NULL CHECK (principle_type IN ('ratio_decidendi', 'obiter_dicta', 'procedural_direction')),
    principle_text text NOT NULL CHECK (length(btrim(principle_text)) >= 20),
    scope text,
    conditions jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(conditions) = 'array'),
    exceptions jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(exceptions) = 'array'),
    applicant_arguments_accepted jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(applicant_arguments_accepted) = 'array'),
    applicant_arguments_rejected jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(applicant_arguments_rejected) = 'array'),
    pio_arguments_accepted jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(pio_arguments_accepted) = 'array'),
    pio_arguments_rejected jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(pio_arguments_rejected) = 'array'),
    outcome text,
    pinpoint_citations jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(pinpoint_citations) = 'array'),
    legal_status text NOT NULL DEFAULT 'pending_review'
        CHECK (legal_status IN ('pending_review', 'verified_current', 'needs_subsequent_review', 'distinguished', 'overruled', 'superseded', 'rejected')),
    subsequent_treatment jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(subsequent_treatment) = 'array'),
    superseded_by_document_id uuid REFERENCES rti.legal_documents(id) ON DELETE RESTRICT,
    reviewer_note text,
    reviewed_by text,
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
      (legal_status <> 'verified_current')
      OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL
          AND length(btrim(COALESCE(reviewer_note, ''))) >= 20
          AND jsonb_array_length(pinpoint_citations) > 0)
    ),
    CHECK (legal_status <> 'overruled' OR superseded_by_document_id IS NOT NULL),
    CHECK (legal_status <> 'superseded' OR superseded_by_document_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_legal_principles_status ON rti.legal_principles (legal_status, principle_type);
CREATE INDEX IF NOT EXISTS idx_legal_principles_document ON rti.legal_principles (document_id);
CREATE INDEX IF NOT EXISTS idx_legal_principles_conditions ON rti.legal_principles USING GIN (conditions);
CREATE INDEX IF NOT EXISTS idx_legal_principles_treatment ON rti.legal_principles USING GIN (subsequent_treatment);
ALTER TABLE rti.legal_principles ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE rti.legal_principles FROM anon, authenticated;
