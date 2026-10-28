-- 003_storage_metadata.sql
-- Documentation of Supabase Storage bucket conventions used by BrandProof AI.
-- This migration does not create any database objects; it only records the intended bucket names
-- and path patterns for future reference. Supabase Storage buckets are managed outside of the
-- PostgreSQL schema, but keeping the conventions version‑controlled helps coordinate backend
-- developers and deployment pipelines.

/*
Bucket names (private by default):
  brand-assets           – approved logos, images, fonts, etc.
  marketing-content      – user‑uploaded marketing copy, images, videos.
  evidence-documents     – uploaded evidence PDFs, DOCX, etc.
  brand-guidelines       – brand guideline PDFs and reference documents.
  profile-avatars        – optional user profile pictures.
*/

/* Path convention (placeholders are actual UUID values at runtime):
  {workspace_id}/brand-assets/{asset_id}/{filename}
  {workspace_id}/marketing-content/{content_item_id}/{filename}
  {workspace_id}/evidence-documents/{evidence_source_id}/{filename}
  {workspace_id}/brand-guidelines/{guideline_id}/{filename}
  {workspace_id}/profile-avatars/{user_id}/{filename}
*/

-- No SQL statements required here; the buckets are created via Supabase dashboard or CLI.

-- End of 003_storage_metadata.sql
