# BrandProof AI — Backend Integration Guide

This document describes the service interfaces the frontend expects the future backend to fulfil,
the proposed API endpoints, and the unresolved requirements the backend team must decide on.

The frontend is currently running entirely in **demo mode** using deterministic stub services.
Switching to live mode requires implementing the interfaces defined in `src/types/domain.ts`
and updating the service registry at the bottom of `src/services/demo.ts`.

---

## Switching from Demo to Live Mode

In `src/services/demo.ts`, update the registry at the bottom of the file:

```typescript
// Current (demo)
export const IS_DEMO_MODE = true;
export const analysisService: IAnalysisService = demoAnalysisService;
export const historyService: IHistoryService = demoHistoryService;
// ...

// Future (live) — replace with real adapters:
export const IS_DEMO_MODE = false;
export const analysisService: IAnalysisService = liveAnalysisService;
export const historyService: IHistoryService = liveHistoryService;
// ...
```

Live adapters should implement the same interfaces from `src/types/domain.ts`.
UI components import only from the service registry — they never reference demo or live adapters directly.

---

## Service Interfaces

These TypeScript interfaces define what the backend adapters must implement:

```typescript
interface IAnalysisService {
  analyze(request: AnalysisRequest): Promise<Analysis>;
  correct(request: CorrectionRequest): Promise<CorrectionResult>;
  getAnalysis(id: string): Promise<Analysis | null>;
}

interface IHistoryService {
  list(): Promise<Analysis[]>;
  save(analysis: Analysis): Promise<void>;
  delete(id: string): Promise<void>;
  clear(): Promise<void>;
}

interface IFeedbackService {
  save(feedback: FindingFeedback): Promise<void>;
  getForAnalysis(analysisId: string): Promise<FindingFeedback[]>;
  delete(id: string): Promise<void>;
}

interface IBrandService {
  get(): Promise<BrandProfile | null>;
  save(profile: BrandProfile): Promise<void>;
  reset(): Promise<void>;
}
```

Full type definitions are in [`src/types/domain.ts`](./src/types/domain.ts).

---

## Proposed API Endpoints

These are design proposals. The backend team should confirm and adjust schemas.

### Health

```
GET /api/v1/ai/health
Response: { status: "ok", version: string, demoMode: boolean }
```

### Extract Text (from uploaded files)

```
POST /api/v1/ai/extract-text
Content-Type: multipart/form-data
Body: { file: File }
Response: { text: string, pageCount?: number, wordCount?: number }
```

### Analyse Content

```
POST /api/v1/ai/analyze
Content-Type: application/json
Body: AnalysisRequest (see domain.ts)
Response: Analysis object (see domain.ts)
```

The response must include an `id`, `findings[]` with typed `Finding` objects,
and `status` reflecting the outcome.

### Apply Corrections

```
POST /api/v1/ai/correct
Content-Type: application/json
Body: CorrectionRequest
Response: CorrectionResult
```

The backend may return either:
- A full replacement `correctedContent` string (preferred), or
- A list of applied replacement instructions

If a full corrected string is returned, the UI will present it as-is and show a diff.

### Analyse File Upload

```
POST /api/v1/ai/analyze-upload
Content-Type: multipart/form-data
Body: { file: File, context: JSON string of AnalysisRequest metadata }
Response: Analysis object
```

---

## Finding Object Contract

Each `Finding` returned by the backend must include:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✅ | Unique per analysis |
| `category` | FindingCategory | ✅ | See enum in domain.ts |
| `severity` | FindingSeverity | ✅ | critical / major / minor / info |
| `originalExcerpt` | string | ✅ | Exact text from source |
| `suggestedCorrection` | string | ✅ | Replacement text |
| `explanation` | string | ✅ | Human-readable explanation |
| `rule` | string | — | Rule or guideline reference |
| `confidence` | number (0–1) | — | Only include if reliable |
| `sourceOffset` | { start, end } | — | Only include if reliable character offsets |
| `isDemo` | boolean | ✅ | Must be `false` for real results |

---

## Source Offset Handling

The frontend will only attempt to highlight source text if `sourceOffset` is present on a finding.
If offsets are not reliable (e.g. after preprocessing or extraction), omit the field entirely.
**Do not return estimated or approximate offsets** — incorrect highlighting degrades trust.

---

## Unresolved Requirements

The following must be determined before backend integration:

### Authentication
- The frontend has no auth layer. The backend team must decide on the auth mechanism
  (JWT, session cookies, OAuth) and the frontend will implement the appropriate token handling.

### CORS
- The backend must configure CORS to allow requests from the frontend origin.

### Video Processing
- The frontend provides a video upload UI but marks video analysis as "requires backend".
- The backend team must decide on video ingestion method: upload + async transcription,
  streaming, third-party service, etc.
- The frontend expects to poll or receive a webhook/SSE update when transcription completes.

### Brand Guideline Persistence
- Currently brand profiles are stored only in localStorage.
- The backend should provide a user-scoped brand profile API so guidelines persist across devices.

### Feedback & Training Pipeline
- The frontend collects per-finding feedback (genuine error / false positive / stylistic / unsure).
- The backend team must decide whether feedback feeds a training pipeline, a review queue, or analytics.
- **The frontend never claims feedback immediately improves the model** — it simply stores and submits the classification.

### Analysis History Ownership
- Currently history is user-local. If the backend stores history server-side, the frontend
  `IHistoryService` adapter will call the history API instead of localStorage.

### Rate Limiting & Queuing
- If analysis requests are queued asynchronously, the frontend expects a polling or SSE mechanism.
  The `Analysis.status` field supports `"pending"` and `"processing"` states for this purpose.

---

## Data Flow Diagram

```
User Input (text / file)
        │
        ▼
AnalysePage (UI)
        │
        ▼
IAnalysisService.analyze(request)
        │
  ┌─────┴──────┐
  │ Demo mode  │  Live mode
  │ (demo.ts)  │  (future liveAnalysisService.ts)
  └─────┬──────┘
        │
        ▼
Analysis object saved via IHistoryService.save()
        │
        ▼
ReviewPage — Findings tab
        │
        ├──▶ IAnalysisService.correct() → CorrectedContent tab
        │
        └──▶ IFeedbackService.save() → Feedback tab
```
