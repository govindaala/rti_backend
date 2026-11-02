-- Repository path: rti_backend/supabase/migrations/20261102114500_enforce_append_only_legal_principle_audit.sql
-- Audit history cannot be rewritten or deleted by ordinary SQL updates.
CREATE OR REPLACE FUNCTION rti.prevent_legal_principle_review_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'legal principle review history is append-only';
END;
$$;
REVOKE ALL ON FUNCTION rti.prevent_legal_principle_review_mutation() FROM PUBLIC, anon, authenticated;
CREATE TRIGGER legal_principle_reviews_append_only
BEFORE UPDATE OR DELETE ON rti.legal_principle_reviews
FOR EACH ROW EXECUTE FUNCTION rti.prevent_legal_principle_review_mutation();
