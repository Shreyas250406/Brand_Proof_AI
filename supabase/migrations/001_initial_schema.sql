-- 001_initial_schema.sql
-- Supabase-compatible schema for BrandProof AI
-- All tables are workspace scoped via workspace_id foreign key
-- UUID primary keys are generated with gen_random_uuid()

-- Enable pgcrypto extension for UUID generation (Supabase includes it by default)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. User profiles (linked to Supabase Auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL,
    avatar_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    -- Note: auth.users table will be referenced in foreign keys where needed
);

-- 2. Workspaces
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    settings JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_workspace_creator FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE RESTRICT
);

-- 3. Workspace memberships
CREATE TYPE workspace_role AS ENUM ('workspace_admin', 'brand_manager', 'creator', 'reviewer', 'auditor');
CREATE TYPE membership_status AS ENUM ('pending', 'active', 'inactive');

CREATE TABLE IF NOT EXISTS workspace_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role workspace_role NOT NULL,
    membership_status membership_status NOT NULL DEFAULT 'pending',
    invited_by UUID,
    joined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_wm_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_wm_user FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_wm_inviter FOREIGN KEY (invited_by) REFERENCES profiles(id) ON DELETE SET NULL,
    CONSTRAINT uq_wm_workspace_user UNIQUE (workspace_id, user_id)
);

-- 4. Brand knowledge items
CREATE TYPE knowledge_type AS ENUM (
    'brand_guideline','brand_rule','product_fact','terminology','tone_of_voice','policy','approved_claim','other'
);

CREATE TABLE IF NOT EXISTS brand_knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    knowledge_type knowledge_type NOT NULL,
    current_version_id UUID,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ,
    CONSTRAINT fk_bki_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_bki_creator FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_bki_current_version FOREIGN KEY (current_version_id) REFERENCES knowledge_versions(id) ON DELETE SET NULL
);

-- 5. Knowledge versions
CREATE TYPE knowledge_status AS ENUM ('draft','pending_approval','approved','expired','superseded','rejected');

CREATE TABLE IF NOT EXISTS knowledge_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_item_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    status knowledge_status NOT NULL DEFAULT 'draft',
    effective_from TIMESTAMPTZ,
    effective_until TIMESTAMPTZ,
    created_by UUID NOT NULL,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    change_summary TEXT,
    CONSTRAINT fk_kv_item FOREIGN KEY (knowledge_item_id) REFERENCES brand_knowledge_items(id) ON DELETE CASCADE,
    CONSTRAINT fk_kv_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_kv_creator FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_kv_approver FOREIGN KEY (approved_by) REFERENCES profiles(id) ON DELETE SET NULL,
    CONSTRAINT uq_kv_item_version UNIQUE (knowledge_item_id, version_number),
    CONSTRAINT chk_kv_effective CHECK (effective_until IS NULL OR effective_from IS NULL OR effective_until > effective_from)
);

-- 6. Evidence sources
CREATE TYPE source_type AS ENUM ('uploaded_document','web_reference','internal_reference','other');
CREATE TYPE evidence_status AS ENUM ('draft','approved','expired','superseded','archived');

CREATE TABLE IF NOT EXISTS evidence_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source_type source_type NOT NULL,
    storage_bucket TEXT,
    storage_path TEXT,
    external_url TEXT,
    mime_type TEXT,
    file_size_bytes BIGINT,
    checksum TEXT,
    document_text TEXT,
    status evidence_status NOT NULL DEFAULT 'draft',
    effective_from TIMESTAMPTZ,
    effective_until TIMESTAMPTZ,
    uploaded_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_es_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_es_uploader FOREIGN KEY (uploaded_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT chk_es_effective CHECK (effective_until IS NULL OR effective_from IS NULL OR effective_until > effective_from)
);

-- 7. Knowledge version – evidence linking
CREATE TYPE relationship_type AS ENUM ('supports','contradicts','supersedes','relates_to');

CREATE TABLE IF NOT EXISTS knowledge_version_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    knowledge_version_id UUID NOT NULL,
    evidence_source_id UUID NOT NULL,
    relationship_type relationship_type NOT NULL,
    excerpt TEXT,
    page_number INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_kve_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_kve_kv FOREIGN KEY (knowledge_version_id) REFERENCES knowledge_versions(id) ON DELETE CASCADE,
    CONSTRAINT fk_kve_es FOREIGN KEY (evidence_source_id) REFERENCES evidence_sources(id) ON DELETE RESTRICT,
    CONSTRAINT uq_kve UNIQUE (knowledge_version_id, evidence_source_id, relationship_type)
);

-- 8. Brand assets (metadata only)
CREATE TYPE asset_type AS ENUM ('logo','product_image','brand_image','icon','illustration','template','other');
CREATE TYPE asset_status AS ENUM ('draft','pending_approval','approved','rejected','archived');

CREATE TABLE IF NOT EXISTS brand_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    asset_type asset_type NOT NULL,
    storage_bucket TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    width_px INTEGER,
    height_px INTEGER,
    checksum TEXT,
    version_number INTEGER NOT NULL,
    status asset_status NOT NULL DEFAULT 'draft',
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    uploaded_by UUID NOT NULL,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ,
    CONSTRAINT fk_ba_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_ba_uploader FOREIGN KEY (uploaded_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_ba_approver FOREIGN KEY (approved_by) REFERENCES profiles(id) ON DELETE SET NULL,
    CONSTRAINT uq_ba_path UNIQUE (workspace_id, storage_bucket, storage_path)
);

-- 9. Content items (marketing content)
CREATE TYPE content_type AS ENUM ('text','social_post','advertisement','landing_page','document','image','other');
CREATE TYPE content_status AS ENUM (
    'draft','queued_for_analysis','analysing','analysis_complete','changes_in_progress','pending_review','approved','rejected','changes_requested','analysis_failed','archived'
);

CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    title TEXT NOT NULL,
    content_type content_type NOT NULL,
    channel TEXT,
    current_version_id UUID,
    status content_status NOT NULL DEFAULT 'draft',
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ,
    CONSTRAINT fk_ci_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_ci_creator FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_ci_current_version FOREIGN KEY (current_version_id) REFERENCES content_versions(id) ON DELETE SET NULL
);

-- 10. Content versions
CREATE TABLE IF NOT EXISTS content_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    content_item_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    text_content TEXT,
    content_metadata JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    change_summary TEXT,
    CONSTRAINT fk_cv_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_cv_item FOREIGN KEY (content_item_id) REFERENCES content_items(id) ON DELETE CASCADE,
    CONSTRAINT fk_cv_creator FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT uq_cv_item_version UNIQUE (content_item_id, version_number)
);

-- 11. Content attachments (files linked to a specific version)
CREATE TYPE attachment_type AS ENUM ('image','document','video','other');

CREATE TABLE IF NOT EXISTS content_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    content_item_id UUID NOT NULL,
    content_version_id UUID NOT NULL,
    storage_bucket TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    checksum TEXT,
    attachment_type attachment_type NOT NULL,
    width_px INTEGER,
    height_px INTEGER,
    uploaded_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_ca_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_ca_item FOREIGN KEY (content_item_id) REFERENCES content_items(id) ON DELETE CASCADE,
    CONSTRAINT fk_ca_version FOREIGN KEY (content_version_id) REFERENCES content_versions(id) ON DELETE CASCADE,
    CONSTRAINT fk_ca_uploader FOREIGN KEY (uploaded_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT uq_ca_path UNIQUE (workspace_id, storage_bucket, storage_path)
);

-- 12. Analysis runs
CREATE TYPE analysis_status AS ENUM ('queued','running','completed','partially_completed','failed','cancelled');

CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    content_item_id UUID NOT NULL,
    content_version_id UUID NOT NULL,
    status analysis_status NOT NULL DEFAULT 'queued',
    engine_name TEXT NOT NULL,
    engine_version TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_code TEXT,
    error_summary TEXT,
    configuration JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_ar_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_ar_content_item FOREIGN KEY (content_item_id) REFERENCES content_items(id) ON DELETE RESTRICT,
    CONSTRAINT fk_ar_content_version FOREIGN KEY (content_version_id) REFERENCES content_versions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_ar_creator FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE RESTRICT
);

-- 13. Analysis – knowledge snapshot (which knowledge versions were visible)
CREATE TABLE IF NOT EXISTS analysis_knowledge_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    analysis_run_id UUID NOT NULL,
    knowledge_version_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_aks_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_aks_run FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE,
    CONSTRAINT fk_aks_kv FOREIGN KEY (knowledge_version_id) REFERENCES knowledge_versions(id) ON DELETE RESTRICT,
    CONSTRAINT uq_aks_run_kv UNIQUE (analysis_run_id, knowledge_version_id)
);

-- 14. Findings
CREATE TYPE finding_category AS ENUM (
    'brand_voice','grammar','terminology','product_fact','promotional_claim','visual_identity','accessibility','cross_content_consistency','guideline_conflict','other'
);
CREATE TYPE severity_level AS ENUM ('low','medium','high','critical');
CREATE TYPE claim_outcome AS ENUM ('supported','contradicted','unverified','needs_human_review','not_applicable');
CREATE TYPE finding_status AS ENUM ('open','accepted','rejected','edited','resolved','unresolved');

CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    analysis_run_id UUID NOT NULL,
    category finding_category NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity severity_level NOT NULL,
    status finding_status NOT NULL DEFAULT 'open',
    claim_outcome claim_outcome,
    affected_text TEXT,
    location_metadata JSONB,
    suggested_correction TEXT,
    confidence NUMERIC CHECK (confidence >= 0 AND confidence <= 1),
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    rule_version_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_f_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_f_run FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE,
    CONSTRAINT fk_f_rule_version FOREIGN KEY (rule_version_id) REFERENCES knowledge_versions(id) ON DELETE SET NULL
);

-- 15. Finding evidence links
CREATE TABLE IF NOT EXISTS finding_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    finding_id UUID NOT NULL,
    evidence_source_id UUID,
    knowledge_version_id UUID,
    relationship_type relationship_type NOT NULL,
    excerpt TEXT,
    page_number INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_fe_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_fe_finding FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE,
    CONSTRAINT fk_fe_es FOREIGN KEY (evidence_source_id) REFERENCES evidence_sources(id) ON DELETE SET NULL,
    CONSTRAINT fk_fe_kv FOREIGN KEY (knowledge_version_id) REFERENCES knowledge_versions(id) ON DELETE SET NULL,
    CONSTRAINT chk_fe_one_source CHECK (
        (evidence_source_id IS NOT NULL)::integer + (knowledge_version_id IS NOT NULL)::integer >= 1
    )
);

-- 16. Finding visual references (optional)
CREATE TABLE IF NOT EXISTS finding_visual_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    finding_id UUID NOT NULL,
    content_attachment_id UUID NOT NULL,
    region_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_fvr_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_fvr_finding FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE,
    CONSTRAINT fk_fvr_attachment FOREIGN KEY (content_attachment_id) REFERENCES content_attachments(id) ON DELETE RESTRICT
);

-- 17. Suggestion decisions
CREATE TYPE decision_type AS ENUM ('accepted','rejected','edited');

CREATE TABLE IF NOT EXISTS suggestion_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    finding_id UUID NOT NULL,
    content_version_id UUID NOT NULL,
    user_id UUID NOT NULL,
    decision decision_type NOT NULL,
    original_text TEXT,
    suggested_text TEXT,
    edited_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_sd_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_sd_finding FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE RESTRICT,
    CONSTRAINT fk_sd_content_version FOREIGN KEY (content_version_id) REFERENCES content_versions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_sd_user FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE RESTRICT
);

-- 18. Reviews
CREATE TYPE review_decision AS ENUM ('approved','rejected','changes_requested');

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    content_item_id UUID NOT NULL,
    content_version_id UUID NOT NULL,
    reviewer_id UUID NOT NULL,
    decision review_decision NOT NULL,
    comments TEXT,
    override_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_rev_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_rev_content_item FOREIGN KEY (content_item_id) REFERENCES content_items(id) ON DELETE RESTRICT,
    CONSTRAINT fk_rev_content_version FOREIGN KEY (content_version_id) REFERENCES content_versions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_rev_reviewer FOREIGN KEY (reviewer_id) REFERENCES profiles(id) ON DELETE RESTRICT
);

-- 19. Audit events
CREATE TYPE event_type AS ENUM ('membership_change','knowledge_create','knowledge_edit','knowledge_approve','knowledge_expire','knowledge_supersede','content_upload','content_edit','analysis_start','analysis_complete','suggestion_decision','review_decision','asset_upload','asset_approve','guideline_proposal','guideline_approval');

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    actor_id UUID,
    event_type event_type NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_audit_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_id) REFERENCES profiles(id) ON DELETE SET NULL
);

-- 20. Guideline improvement proposals
CREATE TYPE proposal_status AS ENUM ('proposed','under_review','approved','rejected','implemented');

CREATE TABLE IF NOT EXISTS guideline_improvement_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    proposed_change TEXT,
    related_knowledge_item_id UUID,
    status proposal_status NOT NULL DEFAULT 'proposed',
    proposed_by UUID NOT NULL,
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    review_comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_gip_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_gip_related_item FOREIGN KEY (related_knowledge_item_id) REFERENCES brand_knowledge_items(id) ON DELETE SET NULL,
    CONSTRAINT fk_gip_proposer FOREIGN KEY (proposed_by) REFERENCES profiles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_gip_reviewer FOREIGN KEY (reviewed_by) REFERENCES profiles(id) ON DELETE SET NULL
);

-- End of 001_initial_schema.sql
