-- seed.sql
-- Synthetic demo data for BrandProof AI.
-- All rows are marked as demo data via comments; they do NOT represent real customers.
-- Adjust UUIDs as needed; they are generated with gen_random_uuid() for convenience.

-- Insert a demo user profile (replace with an existing auth.users UUID when deploying to Supabase)
INSERT INTO profiles (id, display_name, avatar_path, created_at, updated_at)
VALUES (gen_random_uuid(), 'Demo User', NULL, now(), now());

-- Insert a demo workspace
INSERT INTO workspaces (id, name, slug, description, settings, created_by, created_at, updated_at)
VALUES (gen_random_uuid(), 'Demo Workspace', 'demo-workspace', 'Synthetic demo workspace for local testing', '{}', (SELECT id FROM profiles LIMIT 1), now(), now());

-- Workspace membership (admin role)
INSERT INTO workspace_memberships (id, workspace_id, user_id, role, membership_status, invited_by, joined_at, created_at, updated_at)
SELECT gen_random_uuid(), w.id, p.id, 'workspace_admin', 'active', NULL, now(), now(), now()
FROM workspaces w, profiles p
WHERE w.slug = 'demo-workspace' AND p.display_name = 'Demo User';

-- Brand knowledge item and version
INSERT INTO brand_knowledge_items (id, workspace_id, title, description, knowledge_type, created_by, created_at, updated_at)
SELECT gen_random_uuid(), w.id, 'Brand Voice Guidelines', 'Guidelines for brand tone and voice', 'tone_of_voice', p.id, now(), now()
FROM workspaces w, profiles p
WHERE w.slug = 'demo-workspace' AND p.display_name = 'Demo User';

INSERT INTO knowledge_versions (id, knowledge_item_id, workspace_id, version_number, content, status, created_by, created_at, change_summary)
SELECT gen_random_uuid(), ki.id, w.id, 1, 'Use friendly, conversational tone.', 'approved', p.id, now(), 'Initial approved version'
FROM brand_knowledge_items ki
JOIN workspaces w ON ki.workspace_id = w.id
JOIN profiles p ON p.display_name = 'Demo User'
WHERE ki.title = 'Brand Voice Guidelines';

-- Update current_version_id on the knowledge item
UPDATE brand_knowledge_items ki
SET current_version_id = kv.id
FROM knowledge_versions kv
WHERE ki.id = kv.knowledge_item_id AND kv.version_number = 1;

-- Evidence source (uploaded document)
INSERT INTO evidence_sources (id, workspace_id, title, description, source_type, storage_bucket, storage_path, mime_type, file_size_bytes, uploaded_by, created_at, updated_at)
SELECT gen_random_uuid(), w.id, 'Company Policy PDF', 'Company policy document for reference.', 'uploaded_document', 'evidence-documents', 'demo-workspace/evidence-documents/policy.pdf', 'application/pdf', 123456, p.id, now(), now()
FROM workspaces w, profiles p
WHERE w.slug = 'demo-workspace' AND p.display_name = 'Demo User';

-- Link knowledge version to evidence source
INSERT INTO knowledge_version_evidence (id, workspace_id, knowledge_version_id, evidence_source_id, relationship_type, excerpt, created_at)
SELECT gen_random_uuid(), w.id, kv.id, es.id, 'supports', 'Our tone matches the policy guidelines.', now()
FROM knowledge_versions kv
JOIN brand_knowledge_items ki ON kv.knowledge_item_id = ki.id
JOIN workspaces w ON kv.workspace_id = w.id
JOIN evidence_sources es ON es.workspace_id = w.id
WHERE ki.title = 'Brand Voice Guidelines' AND es.title = 'Company Policy PDF';

-- Content item and version
INSERT INTO content_items (id, workspace_id, title, content_type, channel, status, created_by, created_at, updated_at)
SELECT gen_random_uuid(), w.id, 'Spring Campaign Email', 'text', 'email', 'draft', p.id, now(), now()
FROM workspaces w, profiles p
WHERE w.slug = 'demo-workspace' AND p.display_name = 'Demo User';

INSERT INTO content_versions (id, workspace_id, content_item_id, version_number, text_content, created_by, created_at, change_summary)
SELECT gen_random_uuid(), w.id, ci.id, 1, 'Welcome to our Spring Sale! Enjoy 20% off all products.', p.id, now(), 'Initial draft'
FROM content_items ci
JOIN workspaces w ON ci.workspace_id = w.id
JOIN profiles p ON p.display_name = 'Demo User'
WHERE ci.title = 'Spring Campaign Email';

-- Update current_version_id on content item
UPDATE content_items ci
SET current_version_id = cv.id
FROM content_versions cv
WHERE ci.id = cv.content_item_id AND cv.version_number = 1;

-- Analysis run (queued)
INSERT INTO analysis_runs (id, workspace_id, content_item_id, content_version_id, status, engine_name, created_by, created_at)
SELECT gen_random_uuid(), w.id, ci.id, cv.id, 'queued', 'brandproof-engine', p.id, now()
FROM content_items ci
JOIN content_versions cv ON ci.current_version_id = cv.id
JOIN workspaces w ON ci.workspace_id = w.id
JOIN profiles p ON p.display_name = 'Demo User'
WHERE ci.title = 'Spring Campaign Email';

-- Finding (example)
INSERT INTO findings (id, workspace_id, analysis_run_id, category, title, description, severity, status, claim_outcome, affected_text, confidence, requires_human_review, created_at, updated_at)
SELECT gen_random_uuid(), w.id, ar.id, 'brand_voice', 'Tone mismatch', 'The email tone is too formal compared to brand guidelines.', 'medium', 'open', 'contradicted', 'Welcome to our Spring Sale!', 0.85, TRUE, now(), now()
FROM analysis_runs ar
JOIN workspaces w ON ar.workspace_id = w.id
WHERE ar.status = 'queued';

-- Suggestion decision (rejected)
INSERT INTO suggestion_decisions (id, workspace_id, finding_id, content_version_id, user_id, decision, original_text, suggested_text, created_at)
SELECT gen_random_uuid(), w.id, f.id, cv.id, p.id, 'rejected', 'Welcome to our Spring Sale!', 'Hey there! Check out our Spring Sale!', now()
FROM findings f
JOIN analysis_runs ar ON f.analysis_run_id = ar.id
JOIN content_versions cv ON ar.content_version_id = cv.id
JOIN workspaces w ON f.workspace_id = w.id
JOIN profiles p ON p.display_name = 'Demo User'
WHERE f.title = 'Tone mismatch';

-- Review (pending)
INSERT INTO reviews (id, workspace_id, content_item_id, content_version_id, reviewer_id, decision, created_at)
SELECT gen_random_uuid(), w.id, ci.id, cv.id, p.id, 'changes_requested', now()
FROM content_items ci
JOIN content_versions cv ON ci.current_version_id = cv.id
JOIN workspaces w ON ci.workspace_id = w.id
JOIN profiles p ON p.display_name = 'Demo User'
WHERE ci.title = 'Spring Campaign Email';

-- Audit event example
INSERT INTO audit_events (id, workspace_id, actor_id, event_type, entity_type, entity_id, description, metadata, created_at)
SELECT gen_random_uuid(), w.id, p.id, 'content_upload', 'content_items', ci.id, 'Demo user uploaded a new content item.', '{}', now()
FROM content_items ci
JOIN workspaces w ON ci.workspace_id = w.id
JOIN profiles p ON p.display_name = 'Demo User'
WHERE ci.title = 'Spring Campaign Email';

-- Guideline improvement proposal example
INSERT INTO guideline_improvement_proposals (id, workspace_id, title, description, proposed_change, related_knowledge_item_id, status, proposed_by, created_at, updated_at)
SELECT gen_random_uuid(), w.id, 'Add friendly greeting', 'Current guidelines lack a greeting example.', 'Add "Hey there!" as a friendly opening.', ki.id, 'proposed', p.id, now(), now()
FROM brand_knowledge_items ki
JOIN workspaces w ON ki.workspace_id = w.id
JOIN profiles p ON p.display_name = 'Demo User'
WHERE ki.title = 'Brand Voice Guidelines';

-- End of seed.sql
