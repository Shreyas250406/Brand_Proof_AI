# BrandProof AI — Project Log & Feature Documentation

> **Status:** Phase 1 & Multimedia Evolution Complete  
> **Backend Engine:** FastAPI, Google Gemini 3.5 Flash, Groq Whisper Large v3 Turbo, PaddleOCR  
> **Frontend Engine:** React 19, TypeScript, Vite, Tailwind CSS, Radix UI  
> **Database & Storage:** Supabase (PostgreSQL, Auth, RLS), S3-compatible storage  
> **Last Updated:** 31 October 2026  

---

## 1. Executive Summary

**BrandProof AI** is an enterprise-grade multimodal brand compliance, grammar proofreading, and content audit platform. It ingests marketing and corporate communications across **Text**, **Documents**, **Images**, **Audio (Speech)**, and **Video**, detects grammar, spelling, clarity, and brand rule violations, assigns exact timestamps to spoken and visual errors, and generates 2-page publication-ready audit reports with red-underlined errors and AI guideline proofs.

---

## 2. Completed Tabs & Frontend Features

### A. Dashboard / Overview Tab (`OverviewPage.tsx`)
- **Real-time Metric Counters**:
  - **Total Analyses**: Persisted count of all analyses performed by the authenticated user.
  - **Critical / High Issues**: Tally of urgent brand or grammatical violations requiring immediate remediation.
  - **Pending Reviews**: Analyses awaiting human sign-off before publishing.
  - **Quality Health Score**: Dynamically calculated percentage score (0–100%) reflecting overall brand adherence.
- **Recent Analyses Stream**: Quick-access cards displaying recent text, image, audio, and video audits with issue tags and one-click reopening in the Review Workspace.
- **Brand Health Trend Visualization**: Interactive visual charting of error categories over time.

### B. Upload & Analyse Tab (`AnalysePage.tsx`)
Featuring a tabbed interface with three dedicated input channels:

1. **Text Input Tab**:
   - Monospace editor with live word count and character count.
   - One-click **"Load sample text"** shortcut for instant testing of common grammar, spelling, and brand guideline issues.
2. **Documents & Images Tab**:
   - Drag-and-drop file upload zone supporting text documents (`.txt`, `.md`, `.csv`, `.pdf`, `.docx`) and marketing imagery (`.png`, `.jpg`, `.jpeg`, `.webp`).
   - Integrated image OCR pipeline powered by PaddleOCR.
3. **Speech & Video Tab (New Feature)**:
   - Drag-and-drop media zone supporting Audio (`.mp3`, `.wav`, `.m4a`) and Video (`.mp4`, `.mov`, `.webm`) up to 100MB.
   - **Interactive Live Player**: Native `<audio controls>` or `<video controls>` to preview and playback media before analysis.
   - **One-Click Quick Loaders**:
     - *Load sample speech (MP3)*
     - *Load sample video (MP4)*
   - **Pipeline Indicators**: Live badges for *Groq Whisper STT*, *1 FPS PaddleOCR*, and *Second-by-Second Error Timestamps*.
4. **Contextual Analysis Drawer (All Channels)**:
   - Target Audience selector (`General public`, `Business professionals`, `Technical experts`, etc.).
   - Content Type classification (`Blog post`, `Press release`, `Marketing copy`, `Social media`, etc.).
   - Language dialect selector (`English UK`, `English US`, etc.).
   - Custom Writing Instructions and Brand Profile toggle.

### C. Review Workspace Tab (`ReviewPage.tsx`)
- **Split-Screen Review Workspace**:
  - **Left Pane**: Original content with flagged errors, category tags, and severity badges (`Critical`, `Major`, `Minor`, `Info`).
  - **Timestamp Badges**: Spoken and on-screen errors display exact time markers (e.g., `⏱️ 00:04`, `⏱️ 01:23`).
  - **Modality Badges**: Clear differentiation between `🎙️ Speech`, `📺 Visual`, and `🔄 Alignment` contradictions.
- **Selective Correction Engine**:
  - Checkboxes to approve, reject, or bulk-apply AI recommendations.
  - Conflict resolution preventing conflicting replacements.
- **Interactive Inline Editor**: Direct manual refinement of the corrected text.
- **Download Audit Report Button**: Downloads a standardized 2-page PDF audit report with red underlines and proof matrix.

### D. Brand Knowledge Tab (`BrandPage.tsx`)
- **Clean Input Textboxes**: All text boxes display clear, descriptive placeholder hints when empty rather than hardcoded dummy values.
- **Brand Identity**: Brand Name and Brand Mission / Description.
- **Voice & Tone Guidelines**: Configurable tone attributes (approachable, authoritative, warm, etc.).
- **Target Audience Definitions**: Enterprise persona definitions.
- **Preferred Terminology & Prohibited Phrases**: Tag-based editors for whitelist and blacklist terms.
- **Writing Rules**: Numbered custom organizational guidelines (e.g., active voice, sentence length limits).
- **Brand-Specific Instructions & Internal Notes**: Contextual guidance passed to the LLM during prompt formulation.

### E. History Tab (`HistoryPage.tsx`)
- **Direct Supabase Sync**: Real-time retrieval of persisted analysis records for authenticated users.
- **Filterable & Searchable**: Filter by source type (Text, Image, Audio, Video), status, or date range.
- **Reopen in Workspace**: Reopens past analyses with original excerpts, findings, and reviewer progress intact.

### F. Authentication (`AuthPage.tsx`)
- Secure Supabase Auth supporting Email & Password registration and login.
- **1-Click "Demo Admin Login"**: Instant sign-in for evaluators and judges without manual credential typing.

---

## 3. Multimodal AI Processing Workflow

```
                               ┌──────────────────────────────────────────────────────────┐
                               │                    USER INPUT CHANNELS                   │
                               └──────┬────────────────────┬────────────────────┬─────────┘
                                      │                    │                    │
                          [Plain Text / Docs]       [Marketing Images]    [Audio / Video Media]
                                      │                    │                    │
                                      ▼                    ▼                    ▼
                           ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
                           │ Text Normalizer  │ │ OpenCV +         │ │ Audio: Groq Whisper  │
                           │ & Boundary Check │ │ PaddleOCR Engine │ │ Video: FFmpeg +      │
                           │                  │ │ (Text Extraction)│ │ 1 FPS Frame Sampling │
                           └──────────┬───────┘ └──────────┬───────┘ └──────────┬───────────┘
                                      │                    │                    │
                                      ▼                    ▼                    ▼
                                ┌─────────────────────────────────────────────────────┐
                                │          GEMINI 3.5 FLASH PROOFREADING ENGINE       │
                                │                                                     │
                                │  - Context-Aware Prompt Formulation                 │
                                │  - Brand Guidelines & Whitelist/Blacklist Injection │
                                │  - Grammar, Spelling, Style, and Voice Evaluation   │
                                │  - Error Timestamp Resolution (Speech & Visual)     │
                                │  - Cross-Modal Message Consistency Check            │
                                └──────────────────────────┬──────────────────────────┘
                                                           │
                                                           ▼
                                ┌─────────────────────────────────────────────────────┐
                                │           STANDARDIZED ANALYSIS OUTPUT              │
                                │                                                     │
                                │  - Unified Findings List with Exact Timestamps      │
                                │  - Publication-Ready Corrected Copy                 │
                                │  - Issue Summary & Health Metrics                   │
                                └──────────────────────────┬──────────────────────────┘
                                                           │
                                            ┌──────────────┴──────────────┐
                                            ▼                             ▼
                            ┌───────────────────────────────┐ ┌───────────────────────┐
                            │      SUPABASE PERSISTENCE     │ │  REPORTLAB GENERATOR  │
                            │  - public.media_analysis      │ │  - Page 1: Red Errors │
                            │  - public.analysis_history    │ │  - Page 2: AI Proofs  │
                            └───────────────────────────────┘ └───────────────────────┘
```

### Detailed Pipeline Breakdown

1. **Audio (MP3 / WAV / M4A) Pipeline**:
   - Sent to Groq Speech-to-Text utilizing `whisper-large-v3-turbo` with `response_format="verbose_json"`.
   - Groq returns full transcript alongside chronological speech segments with second-by-second start/end timestamps.
   - For large files (>24MB), the engine automatically splits audio into chronological chunks via FFmpeg, transcribes each segment, and reconstructs the timeline.
   - Gemini evaluates the transcript against brand rules and attaches timestamps (`MM:SS`) to every flagged spoken excerpt.

2. **Video (MP4 / MOV / WEBM) Pipeline**:
   - **Stream Separation**: FFmpeg extracts the audio stream into a 16kHz mono MP3.
   - **Speech Recognition**: The extracted audio stream is transcribed via Groq Whisper to capture speech segments.
   - **Visual Frame Sampling**: OpenCV (`cv2`) samples exactly 1 frame per second (`00:00`, `00:01`, `00:02`, ...).
   - **On-Screen OCR**: Each frame is processed through PaddleOCR to extract readable text.
   - **Consecutive Duplicate Suppression**: Eliminates repetitive text across sequential frames while preserving exact timestamps and retaining text that reappears after intervening segments.
   - **Cross-Modal Consistency**: Gemini proofreads both spoken dialogue and on-screen text, checking for alignment, contradictory claims, pricing discrepancies, and terminology drift.

3. **Text & Document Pipeline**:
   - Direct text normalization and structured prompt formulation with few-shot brand context injection into Gemini 3.5 Flash.

4. **Image OCR Pipeline**:
   - Image safety verification, OpenCV preprocessing, and PaddleOCR extraction feeding extracted text directly into Gemini.

---

## 4. Downloadable PDF Audit Report

Generated on the backend via ReportLab (`report_generator.py`):

- **Page 1: Flagged Errors with Red Underline & Timestamps**:
  - Executive assessment summary with issue tally by severity (`High`, `Medium`, `Low`).
  - Original text block where every flagged error is highlighted with a red underline and anchor footnote (`<u>error</u> [1]`).
  - **Flagged Errors Table**: Lists index, excerpt, category, severity, error timestamp (`[00:15]`), and guideline explanation.
- **Page 2: Publication-Ready Corrected Copy & Guideline Proofs**:
  - Clean publication copy incorporating approved grammatical and brand corrections.
  - **AI Guideline Proofs Matrix**: Connects each correction to its official rule standard, timestamp, and AI reasoning.
  - Reviewer Sign-Off Block for corporate editorial governance.

---

## 5. Database Schema & Tables (Supabase PostgreSQL)

| Table Name | Purpose | Key Columns |
|---|---|---|
| `public.profiles` | User profile information | `id (UUID)`, `display_name`, `updated_at` |
| `public.analysis_history` | Text & image analysis history and dashboard metrics | `id`, `user_id`, `input_type`, `original_text`, `corrected_text`, `findings (JSONB)`, `summary`, `created_at` |
| `public.image_metadata` | Uploaded image records and S3 storage keys | `id`, `user_id`, `file_name`, `s3_key`, `image_url`, `created_at` |
| `public.media_analysis` | Detailed audio & video analysis sessions | `id`, `user_id`, `file_name`, `media_type`, `duration_seconds`, `transcription (JSONB)`, `visual_text (JSONB)`, `combined_analysis (JSONB)`, `summary (JSONB)`, `created_at` |

- **Row Level Security (RLS)** is enforced across all tables: users can only view and update their own records.

---

## 6. Test Suite & Verification Results

### Backend (`pytest`): 27 Passed / 27 Total
- **API Tests (`test_api.py`)**: 12 passed
  - Health check & masked database status
  - Text grammar analysis endpoint
  - Image OCR extraction & analysis endpoint
  - Rate limiting & quota exhaustion handling
  - 2-page PDF audit report generation endpoint
  - Media analysis (`/analyze-media`) endpoint with timestamps
- **Multimedia Tests (`test_speech.py`)**: 15 passed
  - MP3 Groq Whisper transcription
  - MP4 to MP3 FFmpeg conversion
  - Video without audio stream handling
  - 1 FPS OpenCV frame extraction
  - PaddleOCR text extraction
  - Consecutive duplicate text suppression
  - Reappearing text retention across intervening frames
  - Empty OCR frame resilience
  - Gemini speech proofreading
  - Gemini visual text proofreading with timestamps
  - Cross-modal consistency and alignment evaluation
  - Missing Groq API key handling
  - Groq API rate limit / timeout handling
  - Corrupted media file safety
  - Temporary file and directory cleanup

### Frontend Quality Checks
- **OxLint**: `0 warnings, 0 errors` across 29 files.
- **TypeScript & Vite Production Build**: `0 errors`, transformed 2,025 modules in 1.30s.
