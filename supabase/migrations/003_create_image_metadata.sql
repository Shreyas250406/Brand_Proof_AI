-- ==============================================================================
-- BrandProof AI - Migration 003: Create Image Metadata Table
-- Description: Stores metadata and object keys for uploaded images (stored in S3).
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.image_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    analysis_id UUID REFERENCES public.analysis_history(id) ON DELETE CASCADE,
    storage_provider TEXT NOT NULL DEFAULT 's3',
    bucket_name TEXT NOT NULL,
    object_key TEXT NOT NULL UNIQUE,
    original_filename TEXT,
    content_type TEXT NOT NULL,
    file_size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for relational navigation and lookup
CREATE INDEX IF NOT EXISTS idx_image_metadata_user_id 
    ON public.image_metadata (user_id);

CREATE INDEX IF NOT EXISTS idx_image_metadata_analysis_id 
    ON public.image_metadata (analysis_id);

CREATE INDEX IF NOT EXISTS idx_image_metadata_object_key 
    ON public.image_metadata (object_key);

CREATE INDEX IF NOT EXISTS idx_image_metadata_created_at 
    ON public.image_metadata (created_at DESC);
