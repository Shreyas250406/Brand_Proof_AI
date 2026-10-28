-- 002_indexes_and_constraints.sql
-- Additional indexes to improve query performance for common access patterns

-- Indexes on workspace_id for quick filtering (most tables already have implicit index via PK/FK)
CREATE INDEX IF NOT EXISTS idx_profiles_workspace ON profiles(id); -- placeholder if needed

-- Workspace memberships (already has composite unique, index on workspace_id,user_id) – add index on role for admin lookups
CREATE INDEX IF NOT EXISTS idx_wm_role ON workspace_memberships(workspace_id, role);

-- Brand knowledge items: index on workspace_id and knowledge_type for filtering
CREATE INDEX IF NOT EXISTS idx_bki_type ON brand_knowledge_items(workspace_id, knowledge_type);

-- Knowledge versions: index on workspace_id, status, and effective dates for timeline queries
CREATE INDEX IF NOT EXISTS idx_kv_status ON knowledge_versions(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_kv_effective FROM knowledge_versions USING btree (workspace_id, effective_from, effective_until);

-- Evidence sources: index on workspace_id and source_type
CREATE INDEX IF NOT EXISTS idx_es_type ON evidence_sources(workspace_id, source_type);

-- Content items: indexes on workspace_id, status, and content_type
CREATE INDEX IF NOT EXISTS idx_ci_status ON content_items(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ci_type ON content_items(workspace_id, content_type);

-- Content versions: index on workspace_id and version_number (already unique per item)
CREATE INDEX IF NOT EXISTS idx_cv_workspace ON content_versions(workspace_id);

-- Analysis runs: index on workspace_id and status, plus started_at for scheduling
CREATE INDEX IF NOT EXISTS idx_ar_status ON analysis_runs(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ar_started ON analysis_runs(workspace_id, started_at);

-- Findings: indexes on workspace_id, severity, category, and status for dashboard queries
CREATE INDEX IF NOT EXISTS idx_f_severity ON findings(workspace_id, severity);
CREATE INDEX IF NOT EXISTS idx_f_category ON findings(workspace_id, category);
CREATE INDEX IF NOT EXISTS idx_f_status ON findings(workspace_id, status);

-- Suggestion decisions: index on workspace_id and decision type
CREATE INDEX IF NOT EXISTS idx_sd_decision ON suggestion_decisions(workspace_id, decision);

-- Reviews: index on workspace_id and decision
CREATE INDEX IF NOT EXISTS idx_rev_decision ON reviews(workspace_id, decision);

-- Audit events: index on workspace_id, event_type, and created_at for auditing queries
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(workspace_id, event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(workspace_id, created_at);

-- Guideline improvement proposals: index on workspace_id and status
CREATE INDEX IF NOT EXISTS idx_gip_status ON guideline_improvement_proposals(workspace_id, status);

-- Content attachments: index on workspace_id and storage_bucket/path for deduplication checks
CREATE INDEX IF NOT EXISTS idx_ca_path ON content_attachments(workspace_id, storage_bucket, storage_path);

-- Brand assets: index on workspace_id, asset_type, and status
CREATE INDEX IF NOT EXISTS idx_ba_type ON brand_assets(workspace_id, asset_type);
CREATE INDEX IF NOT EXISTS idx_ba_status ON brand_assets(workspace_id, status);

-- End of 002_indexes_and_constraints.sql
