-- ==============================================================================
-- BrandProof AI - Migration 004: Disable Row Level Security
-- Description: Disables Row Level Security on profiles, analysis_history, and image_metadata.
-- Note: Disabling RLS allows backend operations via the service role key or API.
-- Keep the service-role key on the backend, never in frontend client code.
-- ==============================================================================

ALTER TABLE public.profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.image_metadata DISABLE ROW LEVEL SECURITY;
