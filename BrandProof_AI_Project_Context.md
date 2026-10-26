# BrandProof AI --- Complete Product Context and Software Build Specification

> **Purpose of this document:** Give an AI coding agent,
> software-building AI, or development team enough context to understand
> the BrandProof AI hackathon project, its user problem, product
> behavior, differentiators, proposed architecture, safety constraints,
> and implementation priorities without needing to reread the discussion
> transcript.
>
> **Source note:** This specification is grounded in the uploaded
> *BrandProof AI --- Round 1 PPT Preparation --- Chat Transcript* and
> the substantive project decisions recorded in it. The transcript
> summarizes the Inkloom AI / CODEX'48 challenge brief; it is not the
> complete original source brief or a repository/source-code dump. Where
> a detail was proposed rather than confirmed as implemented, it is
> marked as a proposal or implementation decision. Do not represent
> planned capabilities as already implemented.

------------------------------------------------------------------------

## 1. Project identity

-   **Project name:** BrandProof AI
-   **Project category:** AI-powered brand governance, marketing-content
    quality assurance, and evidence-backed compliance review.
-   **Challenge context:** CODEX'48, challenge brief associated with
    Inkloom AI.
-   **Round 1 theme:** "The Plan" --- explain the problem, research,
    solution, technical plan, responsible design, execution plan, and
    expected impact.
-   **Product one-liner:** BrandProof AI checks marketing content
    against an organisation's approved brand guidelines, facts,
    terminology, visual assets, and evidence before publication; it
    explains issues and suggests edits while leaving final approval to
    people.
-   **Core promise:** Make brand review more consistent, traceable,
    evidence-backed, and actionable---not simply generate
    better-sounding marketing copy.

### Product principle

**BrandProof AI is a brand-quality inspector, not an autonomous
publisher.** It should help people detect and resolve risks before
publication. It must show why a finding was raised, distinguish evidence
from inference, and keep people in control of decisions and publication.

------------------------------------------------------------------------

## 2. The problem to solve

Organisations produce marketing content across multiple employees,
teams, agencies, channels, and AI-assisted workflows. Without a central
and reliable review process, content can drift away from approved
company information and brand standards. Errors may not be caught until
after the material has been published.

### 2.1 Main problem categories

1.  **Inconsistent brand messaging**
    -   Contributors use different tones, terminology, phrasing, or
        product descriptions.
    -   Multiple assets in the same campaign may communicate slightly
        different versions of the same message.
    -   Regional or channel-specific content may drift away from the
        approved core message.
2.  **Incorrect, outdated, or unsupported information**
    -   Product facts, offers, dates, figures, or descriptions may be
        wrong or out of date.
    -   Promotional claims may lack approved evidence.
    -   Content may use a statement that sounds plausible but cannot be
        substantiated from the company's approved sources.
3.  **Visual brand inconsistency**
    -   Incorrect, outdated, stretched, or otherwise unapproved logos
        may be used.
    -   Colours and other visual elements may not match the brand's
        defined palette.
    -   Different creative assets may apply the visual identity
        inconsistently.
4.  **Language and communication quality**
    -   Grammar and spelling problems.
    -   Tone that does not match the intended brand voice or audience.
    -   Inconsistent terminology or phrasing.
5.  **Accessibility and publication readiness**
    -   Content may fail accessibility expectations.
    -   Reviewers may lack a single report that shows all detected
        issues and their severity.
    -   Findings may be difficult to trace to the relevant rule or
        source.
6.  **Fragmented review and governance**
    -   Reviewers need to inspect many different content formats and
        guidelines.
    -   Suggested edits may be accepted without a clear record of what
        changed or why.
    -   Recurring issues and unclear guidelines may remain undiscovered.
    -   Confidential brand documents and internal facts require
        controlled access.

### 2.2 The core gap

A generic writing assistant can improve wording but does not necessarily
verify content against the organisation's own approved information. The
project aims to provide one central system to review text and visuals
against the organisation's rules and evidence, explain findings, suggest
corrections, and support a human approval process.

### 2.3 Problem statement for product screens or presentation

> Organisations publish marketing content across many channels and
> contributors, making it difficult to consistently enforce brand
> guidelines and verify product information before publication. Manual
> reviews can be time-consuming and may miss inconsistent messaging,
> incorrect assets, accessibility problems, or unsupported promotional
> claims. BrandProof AI provides a central, explainable review workflow
> that checks content against approved company knowledge, identifies
> potential risks, proposes targeted corrections, and keeps final
> approval with authorised people.

**Evidence discipline:** The transcript identifies these as problem
areas from the challenge brief. It does not provide verified
quantitative evidence of error rates, time saved, or survey percentages.
Do not invent such statistics. If survey results are shown in the
product or pitch, use real collected data and label sample data clearly.

------------------------------------------------------------------------

## 3. Intended users and stakeholders

The product should support people who create, review, govern, and
approve marketing content.

### 3.1 Primary user groups

-   **Marketing content creators:** Upload copy or creative material,
    inspect findings, and selectively apply suggestions.
-   **Brand/marketing managers:** Define brand rules, review reports,
    manage assets, and monitor recurring compliance issues.
-   **Product marketing teams:** Ensure product descriptions and claims
    match approved product information.
-   **Reviewers and approvers:** Review high-risk findings, request
    changes, and approve content for the next workflow stage.
-   **Agencies and external collaborators:** Prepare content for a
    client while being restricted to the client/workspace information
    they are authorised to access.
-   **Governance/compliance stakeholders:** Need traceability, source
    references, risk classification, and revision history.

These are proposed user personas inferred from the challenge
requirements, not a claim that each persona has already been
interviewed.

### 3.2 Suggested roles and permissions

Implement a role model that can be expanded:

  -----------------------------------------------------------------------
  Role                                Main permissions
  ----------------------------------- -----------------------------------
  Workspace Admin                     Manage workspace settings, members,
                                      roles, and integrations

  Brand Manager                       Create/update approved brand
                                      knowledge, guidelines, terminology,
                                      and assets

  Creator                             Upload content, run analysis,
                                      inspect findings, edit content, and
                                      submit for review

  Reviewer/Approver                   Review findings, comment, request
                                      changes, approve or reject content

  Read-only/Auditor                   View authorised reports, source
                                      references, and revision/audit
                                      history
  -----------------------------------------------------------------------

For a hackathon MVP, role handling may be simplified, but user-facing
controls must not imply permissions that the backend does not enforce.

------------------------------------------------------------------------

## 4. Product goals and non-goals

### 4.1 Goals

1.  Create a central, workspace-specific brand knowledge base.
2.  Accept marketing content for review.
3.  Analyse text and, where supported, visual content against approved
    rules and evidence.
4.  Report specific findings with severity, explanation, source, and a
    suggested fix.
5.  Let users choose which corrections to accept, reject, or edit.
6.  Preserve human review and approval for publication-sensitive
    decisions.
7.  Store revision and review history.
8.  Surface recurring issues and potential gaps in the brand guidelines.
9.  Keep customer workspaces and confidential documents appropriately
    isolated.
10. Provide a coherent, demonstrable MVP that can be built and tested
    within a hackathon timeline.

### 4.2 Non-goals for the first MVP

Unless implementation time and the existing repository clearly support
them, do not prioritise: - Automatic publishing to external marketing
platforms. - A fully autonomous agent that changes and publishes content
without approval. - Training a foundation model from scratch. -
Guaranteed factual truth for arbitrary external claims. - Perfect
visual/logo recognition across all possible formats. - A complete
enterprise compliance suite. - Building every possible connector before
the core workflow works.

### 4.3 Definition of success

A user can create or access a workspace, configure approved brand
information, upload a supported content item, run analysis, understand
each finding and its evidence, apply or reject individual suggestions,
submit the result for human review, and inspect the final
report/history.

------------------------------------------------------------------------

## 5. End-to-end user journey

The core workflow discussed for BrandProof AI is:

1.  **Company login**
    -   A user signs in and is taken to their authorised workspace.
    -   Data and brand knowledge are scoped to that workspace.
2.  **Dashboard**
    -   Show recent analyses, items needing review, status summaries,
        common issue categories, and quick actions.
    -   Provide an obvious entry point for `Upload & Analyse` and
        `Brand Knowledge / Detail Input`.
3.  **Brand knowledge setup (`Detail Input`)**
    -   An authorised user adds or uploads:
        -   Brand guidelines and policy documents.
        -   Approved company/product facts.
        -   Preferred and prohibited terminology.
        -   Tone-of-voice rules.
        -   Logos and other approved assets.
        -   Approved colour palette and relevant visual guidance.
        -   Evidence documents for claims.
        -   Version, owner, effective date, and approval status where
            applicable.
    -   The system should distinguish approved/active material from
        draft, expired, or superseded material.
4.  **Upload & Analyse**
    -   A user uploads or enters supported marketing content.
    -   Content types may include text, social posts, advertisements,
        landing-page copy, documents, and images, depending on what the
        MVP actually implements.
    -   Validate file type/size, show processing status, and handle
        unsupported or unreadable files gracefully.
5.  **Analysis**
    -   Extract text from supported inputs.
    -   Check grammar, terminology, tone, brand rules, claims, and
        supported visual properties.
    -   Compare claims against the workspace's approved facts and
        evidence.
    -   Generate structured findings, not just an unstructured AI
        paragraph.
6.  **Findings report**
    -   Display each issue with category, severity, affected
        text/visual, explanation, source evidence,
        confidence/uncertainty, and a proposed correction where
        appropriate.
    -   Distinguish a rule violation from a factual contradiction and
        from a claim that simply lacks enough evidence.
7.  **Selective correction**
    -   Let the user accept, reject, or edit each proposed correction
        independently.
    -   Show original and suggested text.
    -   Do not silently rewrite the entire asset when the user asked to
        resolve selected issues.
    -   Re-run relevant checks after edits when practical.
8.  **Review and approval**
    -   User submits a revised item for review.
    -   Reviewer can approve, reject, or request changes and add
        comments.
    -   High-risk findings should require human attention according to
        configured policy.
    -   Approval status must be explicit and recorded.
9.  **Feedback and revision history**
    -   Store accepted/rejected suggestions, user edits, reviewer
        decisions, and versions.
    -   Use feedback to propose improvements to rules or future
        suggestions; do not silently modify authoritative brand policies
        based on a single user's action.
10. **Governance insights**
    -   Summarise common issues, repeated terminology errors, unresolved
        high-risk findings, and possible contradictions or gaps in the
        brand guidelines.
    -   Clearly indicate the time period and dataset behind each metric.
    -   Separate observed counts from inferred recommendations.

------------------------------------------------------------------------

## 6. Main product modules

### 6.1 Authentication and workspace

**Responsibilities** - Authenticate users. - Associate users with one or
more workspaces. - Enforce workspace-level data isolation. - Enforce
role-based access to guidelines, uploads, findings, and approval
actions.

**Acceptance criteria** - A user cannot retrieve another workspace's
content by changing an identifier in a request. - Protected endpoints
check permissions server-side. - Sign-out and expired sessions are
handled cleanly. - Demo credentials, if used, are clearly limited to the
demo environment.

### 6.2 Dashboard

**Suggested components** - Total analysed items. - Items in draft,
analysis, review, approved, or rejected states. - High-risk findings
awaiting review. - Recent activity. - Frequent issue categories. -
Shortcuts to upload content and manage brand knowledge.

**Requirements** - All counts must derive from real application data. -
Empty states should guide first-time users through setup. - Do not
display fabricated metrics as live company data.

### 6.3 Brand Knowledge Base / Detail Input

**Knowledge categories** - Brand identity and voice. - Rules and
policies. - Approved product/company facts. - Preferred, required, and
prohibited terminology. - Claims and their supporting evidence. -
Approved visual assets, logos, and colour values. - Content examples or
templates, if supported.

**Recommended record metadata** - `workspace_id` - `title` -
`category` - `content` or secure file reference - `status` (draft,
approved, expired, superseded) - `version` - `owner_id` - `created_at`,
`updated_at` - `effective_from`, optional `effective_until` -
`source_type` - `source_reference` - `approval metadata`

**Important behaviour** - Only appropriate, approved and currently
applicable knowledge should be treated as authoritative for compliance
decisions. - The UI must make the status of source material visible. -
If sources conflict or no applicable source exists, the system should
say so instead of silently choosing a fact. - Keep version history so
old analyses can be understood against the knowledge that was active at
the time.

### 6.4 Content intake and asset management

**Initial input modes** - Text pasted into an editor. - Common document
formats if extraction is implemented. - Image upload for advertisements
or creative assets. - Optional URL input only if safely implemented and
supported.

**For every upload** - Validate allowed formats and size. - Store files
securely and associate them with the correct workspace. - Track
processing status and useful errors. - Avoid exposing raw private files
through public URLs. - Handle empty, corrupt, unreadable, or unsupported
content gracefully.

**MVP scope recommendation** Prioritise text and one common image format
before attempting every file type. Add document extraction only when it
can be tested end-to-end.

### 6.5 Analysis engine

The analysis engine should coordinate multiple specialised checks and
return a consistent result schema.

#### A. Text quality

-   Grammar and spelling.
-   Readability and clarity, where useful.
-   Tone alignment with configured brand voice.
-   Preferred/prohibited terminology.
-   Required wording and known style rules.

#### B. Brand and policy compliance

-   Compare content against active approved rules.
-   Identify missing required disclaimers or prohibited phrases only
    when the applicable rule is explicit and available.
-   Explain which rule was applied.

#### C. Claim verification

-   Identify candidate factual/promotional claims.
-   Search the workspace's approved knowledge and evidence.
-   Compare claim and evidence.
-   Return one of the following semantic outcomes:
    -   **Supported:** relevant approved evidence supports the claim
        within its scope.
    -   **Contradicted:** relevant approved evidence conflicts with the
        claim.
    -   **Unverified / insufficient evidence:** the available approved
        sources do not adequately establish whether the claim is
        correct.
    -   **Needs human review:** ambiguity, conflicting sources, high
        risk, or uncertainty requires a reviewer.
-   Include source title/version, a relevant excerpt or snippet, and the
    reasoning for the status.
-   Preserve context, units, dates, qualifiers, and scope when comparing
    numbers or product claims.

**Critical rule:** Lack of evidence does not prove a claim false. The
engine must not convert "not found in approved sources" into "false."

#### D. Visual brand checks

Potential checks include: - OCR text extraction from images. - Logo
presence/identity or basic similarity to approved assets. - Colour
comparison against the configured palette. - Text/visual consistency
with the same campaign's approved message. - Basic accessibility checks,
such as whether text contrast appears insufficient or whether important
text is embedded in an image.

These are proposed capabilities. Implement only the checks the selected
libraries and test data can support; show uncertainty where image
quality, cropping, lighting, or design context makes results unreliable.

#### E. Cross-content consistency

-   Compare a set of campaign assets against the same approved facts and
    message.
-   Detect conflicting product descriptions, prices, dates, figures, and
    terminology across submitted items.
-   Show both locations and the shared rule/source that reveals the
    discrepancy.
-   Do not infer that two statements conflict unless their subject, time
    period, units, and context are comparable.

### 6.6 Findings report

Each finding should be a structured object with fields similar to:

``` json
{
  "id": "finding_id",
  "category": "claim_verification",
  "title": "Claim lacks approved supporting evidence",
  "severity": "high",
  "status": "unverified",
  "location": {
    "type": "text_range",
    "start": 120,
    "end": 164,
    "excerpt": "The original claim text"
  },
  "explanation": "The available approved sources do not establish this claim.",
  "source_references": [
    {
      "source_id": "approved_source_id",
      "title": "Approved product brief",
      "version": "3",
      "excerpt": "Relevant supporting or conflicting text"
    }
  ],
  "suggestion": "A more cautious alternative, if appropriate",
  "confidence": 0.78,
  "requires_human_review": true,
  "rule_id": "rule_id"
}
```

This is a proposed schema, not an existing API contract. Adapt it to the
codebase, but preserve the semantic distinctions.

**Report UI should include** - Summary by severity and category. -
Findings list with filters. - Exact affected content or visual region
when available. - Original wording and proposed alternative. -
Explanation and source references. - Confidence/uncertainty indicator
where meaningful. - Accept, reject, or edit actions for eligible
suggestions. - Human-review indicator. - Export/share option only if
supported and permission-checked.

### 6.7 Correction editor

-   Display the original and suggested version side by side or with
    clear change highlighting.
-   Allow per-finding accept/reject/edit.
-   Keep changes reversible.
-   Preserve untouched text and formatting as much as feasible.
-   Record who made a change and when.
-   Re-run analysis or mark the report stale after content changes.
-   Do not imply that accepting a suggestion equals final approval to
    publish.

### 6.8 Review and approval workflow

Suggested statuses:

`draft → queued_for_analysis → analysing → analysis_complete → changes_in_progress → pending_review → approved`

Additional terminal or exception states may include `rejected`,
`changes_requested`, `analysis_failed`, or `archived`.

**Rules** - State transitions must be validated by the backend. -
Approval requires the appropriate role. - High-risk findings can block
approval or require an explicit reviewer override, depending on
workspace policy. - An override should include the reviewer, timestamp,
and reason. - Record review comments and decisions in an audit trail. -
BrandProof AI does not publish content automatically.

### 6.9 Revision history and feedback

Record: - Content versions. - Analysis runs and their source/rule
versions. - Accepted, rejected, and edited suggestions. - Reviewer
comments and decisions. - Approval overrides and reasons. - Changes to
brand knowledge and rules.

Feedback may be used to: - Improve future recommendation relevance. -
Identify false positives or repeatedly rejected suggestions. - Recommend
clarifying a vague or contradictory guideline. - Highlight rules that
are frequently misunderstood.

**Guardrail:** Feedback must not silently rewrite approved facts or
rules. Any proposed guideline change must be shown to an authorised
person and explicitly approved before becoming authoritative.

### 6.10 Governance dashboard

Possible insights: - Number of items analysed during a selected
period. - Findings by category and severity. - Repeated
terminology/style issues. - Items awaiting review. - Most frequently
triggered rules. - Sources that are expired or in conflict. - Proposed
guideline clarifications. - Cross-content inconsistencies in a campaign.

Metrics must be computed from actual stored records and labelled with
their scope/time period. Do not invent results or present
recommendations as measured facts.

------------------------------------------------------------------------

## 7. Differentiation: why BrandProof AI should be more than a generic checker

The discussion identified four differentiators. Treat these as product
directions and implement them in a coherent order.

### 7.1 Brand Truth Graph

Connect: - Approved facts. - Products and services. - Marketing
claims. - Policies and terminology. - Evidence documents. - Source
versions and approval status. - Content items and findings.

A claim should be traceable to the source(s) used to evaluate it. For an
MVP, this can be represented through relational tables and explicit
links; a specialised graph database is not required unless there is a
demonstrated need.

**Example:** A draft advertisement claims that a product supports a
particular capability. BrandProof AI links the claim to the relevant
product record and approved product documentation, then reports whether
the source supports, contradicts, or fails to establish the claim.

### 7.2 Risk-Adaptive Review

Not all issues have the same risk: - A minor tone inconsistency may be a
low-severity suggestion. - An incorrect product detail may be medium or
high severity depending on context. - An unsupported performance or
effectiveness claim may require human review. - A conflict with an
approved policy may block approval according to workspace rules.

Severity should be based on explicit rules and explainable factors, not
an opaque score alone. Users should be able to see why an item was
escalated.

### 7.3 Self-Improving Brand Guidelines

Detect recurring errors, unclear rules, and conflicts among approved
sources. Generate a **proposed clarification** for a brand manager to
review.

Do not allow the model to change the official guidelines automatically.
A human must approve a change, and the new version must be recorded.

### 7.4 Cross-Format Consistency

Compare related text and visual assets---such as an advertisement,
landing page, and social post---against the same approved facts and
campaign message. Report discrepancies with links to both pieces of
content and the relevant source.

### 7.5 Differentiation priority

For a feasible first version, prioritise: 1. Evidence-backed claim
review with source references. 2. Clear separation of supported,
contradicted, and unverified claims. 3. Risk-based human review. 4.
Traceable brand facts/rules and version history. 5. Cross-content checks
and guideline-improvement insights when time permits.

The quality and transparency of these core features are more important
than a long list of shallow integrations.

------------------------------------------------------------------------

## 8. Proposed technical architecture

**The transcript does not establish that a codebase or stack has already
been implemented.** The following is a proposed stack to guide
implementation. Inspect the actual repository before replacing or adding
technologies.

### 8.1 Candidate stack

  -----------------------------------------------------------------------
  Layer                   Candidate technology    Responsibility
  ----------------------- ----------------------- -----------------------
  Frontend                React + Tailwind CSS    Dashboard, upload flow,
                                                  findings, editor,
                                                  settings, review queue

  Backend API             Python + FastAPI        Authentication
                                                  integration, business
                                                  logic, analysis
                                                  orchestration, APIs

  Relational database     PostgreSQL              Users, workspaces,
                                                  brand rules, facts,
                                                  claims, analyses,
                                                  findings, approvals,
                                                  audit logs

  Document/file storage   Private object storage  Original uploads,
                          or protected local      guideline files,
                          storage for local demo  approved assets

  OCR                     PaddleOCR or another    Extract text from
                          tested OCR library      images

  Text analysis           Deterministic rules +   Grammar, terminology,
                          grammar tool such as    tone and structured
                          LanguageTool + optional explanations
                          LLM                     

  Evidence retrieval      Database search or      Retrieve evidence for
                          retrieval-augmented     claim evaluation
                          generation (RAG) over   
                          approved sources        

  Visual processing       OpenCV and              Colour checks, image
                          image-processing        preprocessing, simple
                          utilities               visual comparisons

  Monitoring              Structured application  Debugging, operational
                          logs; optional metrics  visibility
                          dashboard               

  Authentication          Secure session/JWT      Identity and permission
                          approach appropriate to enforcement
                          the existing project    
  -----------------------------------------------------------------------

Choose dependencies based on the repository, deployment target, time,
and licensing. Do not add a heavyweight service just because it appears
in this table.

### 8.2 Logical architecture

``` text
User / Browser
      |
      v
React UI
  |-- Dashboard
  |-- Brand Knowledge
  |-- Upload & Analyse
  |-- Findings / Corrections
  |-- Review & Approval
  |-- Governance Insights
      |
      v
Backend API (FastAPI or existing backend)
  |-- Authentication & workspace permissions
  |-- Upload validation and file handling
  |-- Analysis orchestration
  |-- Findings and correction management
  |-- Review state machine
  |-- Audit and revision history
      |
      +--------------------+
      |                    |
      v                    v
Relational Database   Private File Storage
      |
      v
Analysis pipeline
  |-- Text extraction / OCR
  |-- Rule and terminology checks
  |-- Grammar / tone checks
  |-- Approved-source retrieval
  |-- Claim evidence evaluation
  |-- Visual checks
  |-- Risk classification
      |
      v
Structured findings with source references
      |
      v
Human correction, review, approval, audit
```

### 8.3 Analysis pipeline requirements

1.  Create an analysis record and associate it with the workspace and
    content version.
2.  Extract text and relevant metadata.
3.  Retrieve the approved, applicable brand rules and evidence sources.
4.  Run deterministic checks first where rules are explicit.
5.  Use AI for tasks that benefit from semantic interpretation, such as
    tone, candidate-claim extraction, or explaining a mismatch.
6.  Validate model output against a schema.
7.  Attach evidence references to claims and compliance findings where
    applicable.
8.  Apply severity/risk rules and human-review requirements.
9.  Persist findings and analysis metadata.
10. Return a clear report and processing status.
11. Handle failures without losing the uploaded item or exposing
    sensitive information.

### 8.4 LLM design requirements

-   Do not treat model output as ground truth.
-   Give the model only the workspace sources it is authorised to
    access.
-   Require structured output for findings.
-   Require source IDs or snippets for evidence-backed claim judgments.
-   If no source is found, return `unverified` or `needs_human_review`,
    not `false`.
-   Validate output before storing or displaying it.
-   Defend against prompt injection inside uploaded documents: document
    text is data to analyse, not instructions that override
    system/application policy.
-   Avoid sending confidential data to external model services unless
    the user/workspace is informed and the integration is authorised.
-   Disclose external AI/service use as required by the challenge and
    product design.

### 8.5 API surface (suggested)

Adapt these routes to existing conventions; they are not mandated names.

-   `POST /auth/...` --- authentication/session handling.
-   `GET /workspaces/current` --- current workspace and permissions.
-   `GET /dashboard/summary` --- real counts and recent activity.
-   `GET /brand-knowledge` --- list authorised knowledge records.
-   `POST /brand-knowledge` --- create a record.
-   `PATCH /brand-knowledge/{id}` --- update a record with version
    history.
-   `POST /brand-knowledge/{id}/submit-for-approval` --- optional
    approval flow for knowledge changes.
-   `POST /content` --- create/upload a content item.
-   `GET /content/{id}` --- retrieve item and status.
-   `POST /content/{id}/analyse` --- start analysis.
-   `GET /analyses/{id}` --- analysis status and findings.
-   `PATCH /findings/{id}` --- record accepted/rejected/edited decision
    where permitted.
-   `POST /content/{id}/submit-review` --- submit content for review.
-   `POST /content/{id}/review-decision` --- approve, reject, or request
    changes.
-   `GET /content/{id}/history` --- revisions and decisions.
-   `GET /governance/insights` --- metrics derived from actual records.

Use asynchronous jobs if analysis takes longer than a normal request.
The UI should poll or subscribe to a status endpoint rather than appear
frozen.

------------------------------------------------------------------------

## 9. Suggested data model

This is a conceptual starting point. Match names, types, and
relationships to the existing repository.

### 9.1 Core entities

-   **User:** identity, status, authentication reference.
-   **Workspace:** company/team boundary and settings.
-   **WorkspaceMembership:** user, workspace, role.
-   **BrandKnowledgeItem:** approved fact, rule, terminology item, or
    policy.
-   **KnowledgeVersion:** immutable or auditable version of a knowledge
    item.
-   **EvidenceSource:** document or reference supporting claims/rules.
-   **BrandAsset:** logo/image/asset, metadata, approved version.
-   **ContentItem:** uploaded content, type, owner, status, current
    version.
-   **ContentVersion:** stored text or file reference, version, author,
    timestamp.
-   **AnalysisRun:** content version, engine/version, source snapshot,
    status, timestamps.
-   **Finding:** category, severity, outcome, location, explanation,
    confidence.
-   **FindingEvidence:** finding-to-source links and excerpts.
-   **SuggestionDecision:** accept/reject/edit, user, time, resulting
    change.
-   **Review:** reviewer, decision, comments, timestamp, override reason
    if applicable.
-   **AuditEvent:** important action, actor, workspace, entity,
    timestamp, metadata.
-   **GuidelineImprovementProposal:** detected ambiguity/recurrence,
    proposed clarification, approval status.

### 9.2 Data principles

-   Workspace-scoped entities should have explicit workspace
    relationships.
-   Enforce access at the server/database layer, not only by hiding UI
    controls.
-   Keep the source/version used for each analysis so old results remain
    explainable.
-   Do not overwrite old approved knowledge without history.
-   Avoid logging secrets, complete confidential documents, or
    unnecessary personal data.
-   Store file references and permissions securely.
-   Use timestamps consistently and define whether they are stored in
    UTC.

------------------------------------------------------------------------

## 10. Responsible AI, privacy, and human control

These are product requirements, not optional polish.

### 10.1 Explainability

Every important finding should answer: - What was flagged? - Where is it
located? - Which rule or approved source was used? - Why does the
content appear inconsistent? - How certain is the system? - What can the
user do next?

### 10.2 Uncertainty and claim truth

-   "Supported" means the retrieved evidence supports the claim within
    its scope; it is not a universal guarantee of truth.
-   "Contradicted" requires relevant evidence that conflicts with the
    claim.
-   "Unverified" means available sources do not adequately establish the
    claim.
-   Conflicting or ambiguous sources should be surfaced.
-   Absence of evidence is not evidence of falsity.
-   High-risk claims should be escalated to a human.

### 10.3 Human control

-   Users select which suggested changes to apply.
-   Reviewers retain approval authority.
-   No automatic publication.
-   High-risk overrides require an authorised reviewer and recorded
    reason where applicable.
-   AI-generated suggestions must be distinguishable from the user's
    original text.

### 10.4 Privacy and security

-   Enforce workspace isolation and least-privilege access.
-   Restrict access to uploaded files and evidence documents.
-   Use secure transport and appropriately protected secrets.
-   Validate file type and size; protect against malicious uploads.
-   Avoid public file URLs for confidential material.
-   Provide clear handling for external AI services and disclose their
    use.
-   Do not use customer documents to train or improve external models
    unless there is explicit authorisation and an appropriate policy.
-   Keep audit history for sensitive changes and approvals.
-   Define retention/deletion behaviour suitable for the prototype and
    disclose limitations.

### 10.5 Accessibility and inclusive use

-   Use semantic structure and keyboard-accessible controls.
-   Provide readable contrast and clear focus indicators.
-   Do not communicate severity through colour alone.
-   Ensure reports use clear language and explain technical terms.
-   Where visual accessibility checks are automated, label them as
    checks or warnings rather than guarantees of accessibility
    conformance.

------------------------------------------------------------------------

## 11. UX and visual design guidance

The interface should feel like a professional enterprise SaaS product
for marketing teams---not a generic chat window.

### 11.1 Main screens

1.  **Login / workspace entry**
2.  **Dashboard**
3.  **Upload & Analyse**
4.  **Analysis progress / processing state**
5.  **Findings report**
6.  **Selective correction editor**
7.  **Brand Knowledge / Detail Input**
8.  **Review queue and approval details**
9.  **Content/revision history**
10. **Governance insights**
11. **Workspace settings and roles**, if included in scope

### 11.2 Interaction priorities

-   Make the primary action obvious.
-   Show upload constraints before a user selects a file.
-   Make analysis status visible.
-   Let users move from a finding to the exact affected content.
-   Show source snippets close to the associated claim judgment.
-   Make accept/reject/edit actions explicit and reversible.
-   Clearly distinguish analysis completion from approval to publish.
-   Include empty, loading, success, partial-result, and error states.
-   Keep dashboard metrics connected to real data.
-   Ensure a first-time user can understand the setup flow without prior
    instruction.

### 11.3 Finding categories for the UI

Suggested category labels: - Brand voice and tone - Grammar and
clarity - Terminology - Approved facts and product information -
Promotional claims - Visual identity - Accessibility - Cross-content
consistency - Guideline conflict or ambiguity

Use plain language and consistent severity labels, such as `low`,
`medium`, `high`, and `critical`, if those levels are implemented.
Define severity semantics and use them consistently.

------------------------------------------------------------------------

## 12. Development plan and scope

The original Round 1 presentation is a plan, not evidence that the
following work is complete. Use the phases below to build a demonstrable
MVP.

### Phase 0 --- Repository and environment audit

-   Inspect existing code, package manifests, database schema, routes,
    authentication, and UI.
-   Identify what is implemented, partially implemented, broken, or
    absent.
-   Run the existing application and tests before major changes.
-   Preserve working functionality and existing user data.
-   Do not replace the framework or database without a clear reason.

**Deliverable:** brief implementation inventory and confirmed local run
instructions.

### Phase 1 --- Core shell and workspace

-   Login or demo authentication appropriate to the existing project.
-   Workspace-aware dashboard.
-   Navigation for knowledge base, uploads, reports, review, and
    insights.
-   Database migrations/schema for core records.
-   Role checks and workspace boundaries.

**Exit condition:** authorised user can navigate the app and see real
empty states/data.

### Phase 2 --- Brand knowledge setup

-   Create/edit approved facts, rules, terminology, and source records.
-   Upload or register evidence documents and assets as supported.
-   Add status/version metadata.
-   Ensure analysis can retrieve only the correct workspace's approved
    knowledge.

**Exit condition:** a test brand can be configured and retrieved
reliably.

### Phase 3 --- Upload and first analysis

-   Support pasted text and one chosen file type first.
-   Persist content and versions.
-   Run deterministic terminology/rule checks.
-   Add grammar/tone or claim analysis only where testable.
-   Persist structured findings.

**Exit condition:** user uploads content and receives a repeatable
report with locations and explanations.

### Phase 4 --- Evidence-backed claim review

-   Extract candidate claims.
-   Retrieve approved source excerpts.
-   Return supported/contradicted/unverified outcomes.
-   Add source/version references.
-   Add human-review routing for uncertain or high-risk claims.

**Exit condition:** a demo can show one supported claim, one
contradicted claim, and one unverified claim without conflating the
outcomes.

### Phase 5 --- Corrections and review workflow

-   Per-finding accept/reject/edit.
-   Versioned content updates.
-   Submit for review.
-   Reviewer decision and comments.
-   Audit trail and history.

**Exit condition:** a full upload → analyse → edit → review → decision
journey works.

### Phase 6 --- Visual checks and governance insights

-   Add OCR for images.
-   Implement a small, reliable set of visual checks.
-   Add cross-content comparison if time permits.
-   Build metrics from actual stored records.
-   Add guideline-improvement proposals with human approval.

**Exit condition:** any implemented visual/insight feature has test
examples and clear limitations.

### Phase 7 --- Hardening and demo readiness

-   Validate permissions and workspace isolation.
-   Test invalid uploads and analysis failures.
-   Test empty and conflicting evidence.
-   Review accessibility and error states.
-   Add sample demo workspace/data that is explicitly synthetic.
-   Document environment variables, setup, limitations, and external
    service usage.
-   Prepare a stable demonstration path.

------------------------------------------------------------------------

## 13. Testing strategy

### 13.1 Functional tests

-   Create/edit approved brand rules.
-   Upload supported content.
-   Run analysis and retrieve results.
-   Accept, reject, and edit suggestions.
-   Submit for review and make a reviewer decision.
-   Inspect revision and audit history.
-   Display dashboard counts based on stored records.

### 13.2 Claim-evaluation test cases

Create controlled fixtures for: 1. A claim explicitly supported by
approved evidence. 2. A claim explicitly contradicted by approved
evidence. 3. A claim for which no evidence exists. 4. Conflicting source
versions. 5. Evidence that is expired or not yet effective. 6. A
numerically similar claim with different units or time scope. 7. A claim
whose wording is ambiguous and requires review.

The expected result must not treat missing evidence as contradiction.

### 13.3 Security tests

-   Attempt to access another workspace's content.
-   Attempt a reviewer-only action as a creator.
-   Attempt an approval without required permission.
-   Upload unsupported or oversized files.
-   Check that secrets and private document contents do not leak into
    client-visible errors or logs.
-   Test malicious instructions embedded in uploaded content.

### 13.4 UX and failure tests

-   Empty dashboard.
-   No approved brand knowledge configured.
-   Upload fails.
-   OCR returns no text.
-   Analysis times out or partially fails.
-   A source is missing or conflicting.
-   A user rejects all suggestions.
-   A reviewer requests changes.
-   A content item is edited after analysis and the report is marked
    stale or re-run.

------------------------------------------------------------------------

## 14. Success metrics

Use these as metrics to instrument, not as results to claim in advance.

-   **Analysis completion rate:** successful analysis runs / started
    analysis runs.
-   **Time to first report:** time between analysis start and usable
    findings.
-   **Finding action rate:** findings accepted, rejected, edited, or
    escalated / total findings.
-   **Human-review completion time:** elapsed time from review
    submission to decision.
-   **Repeated issue rate:** frequency of the same rule/category over a
    defined period.
-   **Evidence coverage:** claim findings with valid source references /
    claim findings requiring evidence.
-   **Unverified claim rate:** claims marked unverified / claims
    analysed.
-   **False-positive feedback rate:** findings users mark as incorrect /
    findings with feedback.
-   **Approval cycle time:** time from first analysis to approval.
-   **Cross-content inconsistency count:** detected inconsistencies
    among linked campaign items.

Report sample size, time range, and definitions. Do not use made-up
percentage improvements in the pitch or dashboard.

------------------------------------------------------------------------

## 15. Hackathon deliverables and evaluation alignment

The challenge brief, as summarised in the transcript, describes three
rounds:

-   **Round 1 --- The Plan:** problem definition/evidence, target
    users/research, proposed solution/workflow, features, technical
    plan, integrations/data sources, responsible design, development
    plan/roles, and expected impact.
-   **Round 2 --- The Build:** functional product/prototype/MVP,
    accessible repository, demo/deployment, architecture and technical
    disclosures, user feedback where available, and team contributions.
-   **Round 3 --- The Finish:** final product/demo, presentation or
    report, testing evidence, privacy/security/accessibility
    explanation, limitations, roadmap, and contribution details.

### Round 1 marking scheme

  Criterion                                   Points
  ---------------------------------------- ---------
  Understanding of the problem statement          25
  Proposed solution                               25
  Technical plan                                  20
  Originality of approach                         15
  Feasibility and scope                           15
  **Total**                                  **100**

The first two criteria account for 50% of the score, so the pitch should
clearly show that the team understands the real governance problem and
has a coherent solution. The technical plan must be credible,
originality must be demonstrated through the differentiators, and scope
must be realistic.

### Round 1 slide plan recorded in the transcript

1.  Problem Statement
2.  Problem Validation --- survey
3.  Target Users
4.  Proposed Solution
5.  End-to-End Workflow
6.  Innovation and Differentiators
7.  Technical Architecture and Tech Stack
8.  Responsible AI, Privacy and Human Control
9.  Development Plan and Team Roles
10. Expected Impact and Success Metrics
11. Conclusion
12. Title Slide --- created last

The team agreed to prepare the content slides first and the title slide
last.

**Survey integrity:** The discussion says a survey was taken from
employees of three companies, but the transcript does not contain a
complete verified dataset or numerical results. Use only actual
responses and actual counts in any evidence section. Any synthetic demo
responses must be labelled as synthetic/illustrative and must not be
attributed to real employees without confirmation.

------------------------------------------------------------------------

## 16. Implementation rules for an AI coding agent

When asked to build or modify this project, follow these rules:

1.  **Inspect before changing.** Read the repository structure, package
    files, environment setup, schema, routes, and existing UI before
    writing code.
2.  **Preserve the current stack by default.** Do not rewrite a working
    project from scratch merely because another stack is suggested here.
3.  **Build vertical slices.** Complete one end-to-end workflow (data
    model → API → UI → tests) before adding many disconnected features.
4.  **Use real persistence.** Do not leave key actions as UI-only mock
    buttons if the application presents them as working features.
5.  **Do not fabricate data.** Seed demo records only when explicitly
    marked as sample/demo data. Never present synthetic survey
    responses, user feedback, company metrics, or analysis results as
    real.
6.  **Keep analysis outputs structured.** Use schemas and validate AI
    output before saving or rendering.
7.  **Keep evidence traceable.** For a claim judgment, preserve the
    source identity and relevant excerpt used by the analysis.
8.  **Represent uncertainty correctly.** Missing evidence is
    `unverified`, not automatically `false`.
9.  **Enforce permissions on the backend.** Frontend-only hiding is
    insufficient.
10. **Keep human approval in control.** Do not add automatic publication
    or silent guideline changes.
11. **Protect confidential material.** Avoid exposing uploads, secrets,
    or cross-workspace data.
12. **Provide clear loading and failure states.** Do not fake success
    when a backend operation fails.
13. **Test important logic.** Include tests for source conflict, missing
    evidence, permission boundaries, and review state transitions.
14. **Document configuration.** Provide `.env.example` with placeholder
    values, never real credentials.
15. **Be transparent about limitations.** If OCR, visual comparison, or
    a model integration is only a prototype, state that accurately in
    the UI and documentation.
16. **Do not claim a feature is finished until it has been implemented
    and tested.**

### Expected coding-agent response before implementation

After inspecting the repository, first summarise: - Existing
architecture and run commands. - What features already exist. - Missing
or broken parts relative to this specification. - Any migration or
security risks. - A phased implementation plan ordered by user-visible
value.

Then implement in small, testable steps and report which parts are
complete versus still proposed.

------------------------------------------------------------------------

## 17. MVP acceptance checklist

A build is a credible BrandProof AI MVP when all essential items below
work:

-   [ ] User can enter an authorised workspace.
-   [ ] Workspace data is isolated.
-   [ ] User can configure approved facts/rules/terminology and their
    source/version.
-   [ ] User can submit supported marketing text or an implemented file
    type.
-   [ ] The system runs analysis and returns structured findings.
-   [ ] Findings show the affected content, explanation, and applicable
    rule/source when available.
-   [ ] Claim outcomes distinguish supported, contradicted, and
    unverified.
-   [ ] Missing evidence does not automatically label a claim false.
-   [ ] Users can accept, reject, or edit eligible suggestions
    individually.
-   [ ] The content's analysis/report is refreshed or marked stale after
    relevant edits.
-   [ ] A human reviewer can make a recorded review decision.
-   [ ] Revision history and important decisions are stored.
-   [ ] Dashboard metrics come from real records.
-   [ ] Errors and limitations are visible and understandable.
-   [ ] Demo data is clearly labelled.
-   [ ] No content is published automatically.
-   [ ] Setup and configuration instructions are documented.

------------------------------------------------------------------------

## 18. Known uncertainties and decisions to make during implementation

The transcript does not specify the following. The coding agent should
inspect the existing repository or ask the project owner before making
high-impact assumptions:

-   Existing source code, framework, database, hosting, and current
    implementation status.
-   Exact supported upload formats and size limits.
-   Authentication provider and account lifecycle.
-   Whether the app is single-company or multi-workspace.
-   Which external LLM/OCR providers are available and permitted.
-   Data retention and deletion requirements.
-   Exact review policies and which findings block approval.
-   Whether integrations with publishing platforms are required.
-   Required deployment target and environment.
-   Team members and their actual responsibilities.
-   Verified survey dataset and any measured research findings.
-   Brand-specific examples, approved source documents, and evaluation
    fixtures.

When a decision is not known, choose a minimal, reversible default and
document it. Do not invent stakeholder requirements or present an
assumption as a confirmed fact.

------------------------------------------------------------------------

## 19. Final product vision

BrandProof AI should become a reliable checkpoint between content
creation and publication. It combines company-specific brand knowledge,
evidence-backed claim review, text and visual checks, explainable
findings, selective corrections, risk-aware human approval, and a
traceable governance history.

Its strongest differentiator is not that it can rewrite marketing copy.
It is that it can explain **which approved rule or evidence supports a
finding, what remains uncertain, how risky the issue is, and what a
human should do next**---without taking control away from the people
responsible for the brand.
