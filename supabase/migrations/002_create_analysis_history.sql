-- ==============================================================================
-- BrandProof AI - Migration 002: Create Analysis History Table
-- Description: Stores text and image analysis history with structured AI findings.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.analysis_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    input_type TEXT NOT NULL CHECK (input_type IN ('text', 'image')),
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    findings JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary TEXT,
    model_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for efficient retrieval by user and chronological history sorting
CREATE INDEX IF NOT EXISTS idx_analysis_history_user_id 
    ON public.analysis_history (user_id);

CREATE INDEX IF NOT EXISTS idx_analysis_history_created_at 
    ON public.analysis_history (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_history_user_created 
    ON public.analysis_history (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_history_input_type 
    ON public.analysis_history (input_type);
