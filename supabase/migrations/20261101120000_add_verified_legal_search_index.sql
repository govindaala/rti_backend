-- रिपॉजिटरी पथ: rti_backend/supabase/migrations/20261101120000_add_verified_legal_search_index.sql
-- Verified legal corpus के title और extracted text पर तेज full-text खोज।
-- यह migration केवल index जोड़ती है; मौजूदा दस्तावेज़/verification status नहीं बदलती।
CREATE INDEX IF NOT EXISTS legal_documents_verified_text_search_idx
  ON rti.legal_documents
  USING GIN (
    to_tsvector(
      'simple',
      COALESCE(title, '') || ' ' || COALESCE(extracted_text, '')
    )
  )
  WHERE status = 'verified' AND extracted_text IS NOT NULL;
