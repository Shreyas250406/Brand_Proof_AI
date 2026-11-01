-- ==============================================================================
-- BrandProof AI - Database Schema: Claim Verifications
-- Description: Stores evidence-based claim verification evaluations and results
--              with Row Level Security enabled for user isolation.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.claim_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    claim TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_status TEXT NOT NULL CHECK (
        verification_status IN (
            'SUPPORTED',
            'CONTRADICTED',
            'PARTIALLY_SUPPORTED',
            'UNVERIFIABLE',
            'CONFLICTING_EVIDENCE'
        )
    ),
    confidence NUMERIC(3, 2),
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for fast retrieval by user and chronological ordering
CREATE INDEX IF NOT EXISTS idx_claim_verifications_user_id 
    ON public.claim_verifications (user_id);

CREATE INDEX IF NOT EXISTS idx_claim_verifications_created_at 
    ON public.claim_verifications (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_claim_verifications_user_created 
    ON public.claim_verifications (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_claim_verifications_status 
    ON public.claim_verifications (verification_status);

-- Enable Row Level Security (RLS)
ALTER TABLE public.claim_verifications ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Authenticated users can only view, insert, and delete their own records
DROP POLICY IF EXISTS "Users can view their own claim verifications" ON public.claim_verifications;
CREATE POLICY "Users can view their own claim verifications"
    ON public.claim_verifications
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own claim verifications" ON public.claim_verifications;
CREATE POLICY "Users can insert their own claim verifications"
    ON public.claim_verifications
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own claim verifications" ON public.claim_verifications;
CREATE POLICY "Users can delete their own claim verifications"
    ON public.claim_verifications
    FOR DELETE
    USING (auth.uid() = user_id);
