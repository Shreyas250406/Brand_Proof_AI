-- ==============================================================================
-- BrandProof AI - Migration 005: Create Media Analysis Table
-- Description: Stores speech transcription, second-by-second visual OCR segments,
--              structured Gemini AI proofreading findings, and combined alignment.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.media_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    media_type TEXT NOT NULL CHECK (media_type IN ('audio', 'video')),
    duration_seconds NUMERIC(10, 2),
    original_filename TEXT,
    transcription JSONB NOT NULL DEFAULT '{}'::jsonb,
    visual_text JSONB NOT NULL DEFAULT '{}'::jsonb,
    combined_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for fast retrieval by user and chronological ordering
CREATE INDEX IF NOT EXISTS idx_media_analysis_user_id 
    ON public.media_analysis (user_id);

CREATE INDEX IF NOT EXISTS idx_media_analysis_created_at 
    ON public.media_analysis (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_analysis_media_type 
    ON public.media_analysis (media_type);

CREATE INDEX IF NOT EXISTS idx_media_analysis_user_created 
    ON public.media_analysis (user_id, created_at DESC);

-- Disable Row Level Security to allow service-role backend operations
ALTER TABLE public.media_analysis DISABLE ROW LEVEL SECURITY;
