# BrandProof AI — Standalone AI Engine

Production-grade, standalone AI engine for **BrandProof AI**. It provides high-precision, context-aware grammar, spelling, punctuation, clarity, and brand-guided text and image analysis via FastAPI and real OCR.

---

## 1. Scope & Architecture

This repository contains **strictly the stateless AI processing layer**:
- **No Frontend or UI.**
- **No Database or Persistent Storage.**
- **No Authentication or User Sessions.**
- **No Mock Responses or Hardcoded Grammar Rules in Runtime.**

The engine is accessible via REST API and can be integrated downstream into any dashboard, queue, or database.

### System Directory Layout

```text
app/
├── main.py                     # FastAPI application entrypoint and middleware
├── api/
│   ├── routes.py               # REST API route handlers (/api/v1/ai/...)
│   └── schemas.py              # Pydantic v2 validation models
├── core/
│   ├── config.py               # Settings management via Pydantic Settings
│   └── exceptions.py           # Domain exceptions and status mapping
├── services/
│   ├── ai_provider.py          # Isolated LLM client provider with retry/timeout logic
│   ├── grammar_analyzer.py     # Structured prompt formulation & schema enforcement
│   ├── correction_generator.py # Validates and finalizes full corrected text
│   ├── ocr_service.py          # Real PaddleOCR text extraction & image validation
│   └── text_processor.py       # Pipeline orchestrator and input normalizer
└── prompts/
    └── grammar_analysis.py     # System instructions and data-boundary framing
tests/
├── conftest.py                 # Pytest fixtures and mock responses
├── test_api.py                 # Integration tests for FastAPI endpoints
├── test_grammar_analyzer.py    # Grammar, style, ambiguity, and LLM error tests
├── test_ocr_service.py         # Real PaddleOCR extraction and image safety tests
└── test_reliability_security.py# Boundary checks, limits, and injection resistance
```

---

## 2. Dependencies & Prerequisites

- **Python:** 3.10+ (tested on Python 3.12)
- **Framework:** FastAPI, Uvicorn, Pydantic v2
- **LLM Engine:** Google Gemini (default: `gemini-2.5-flash`, ultra-low credit usage and high efficiency)
- **Speech-to-Text:** Groq Whisper (`whisper-large-v3-turbo`)
- **OCR Engine:** PaddleOCR 3.x with PaddlePaddle backend
- **Media Processing:** OpenCV, FFmpeg / `imageio-ffmpeg`
- **PDF Report Generation:** ReportLab

Install all dependencies:

```bash
pip install -r requirements.txt
```

---

## 3. Environment Configuration

Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

### Supported Settings

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `gemini` | AI Provider: `gemini` (default), `google`, or `custom` |
| `AI_MODEL` | `gemini-2.5-flash` | Gemini model (e.g., `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`) |
| `GEMINI_API_KEY` | *(None)* | Your Google Gemini API key from Google AI Studio |
| `AI_API_KEY` | *(None)* | Alternative API key variable |
| `AI_BASE_URL` | *(None)* | Optional custom endpoint |
| `AI_TIMEOUT_SECONDS` | `30.0` | Timeout threshold for AI provider calls |
| `AI_MAX_RETRIES` | `2` | Number of automatic retries on transient errors |
| `GROQ_API_KEY` | *(None)* | Your Groq Cloud API key for Whisper speech transcription |
| `GROQ_MODEL` | `whisper-large-v3-turbo` | Groq Whisper model ID |
| `FFMPEG_BINARY` | *(Auto)* | Optional explicit path to FFmpeg binary |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum uploaded image size limit (in MB) |
| `MAX_TEXT_LENGTH` | `50000` | Maximum input text character length |
| `OCR_ENGINE` | `paddleocr` | OCR engine to use |
| `OCR_LANG` | `en` | OCR recognition language |
| `OCR_USE_GPU` | `false` | Whether to use GPU acceleration for OCR |

> [!NOTE]
> On Windows CPU environments, `FLAGS_use_onednn=0` and `FLAGS_use_mkldnn=0` are automatically enforced by the engine to guarantee stability against oneDNN instruction mismatches.

---

## 4. Running the Engine

Start the development server with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 5. API Reference & Examples

### 1. Health Check
`GET /api/v1/ai/health`

Verifies engine health, OCR availability, and AI provider configuration without leaking any secrets.

#### Example Request:
```bash
curl -X GET http://127.0.0.1:8000/api/v1/ai/health
```

#### Example Response:
```json
{
  "status": "healthy",
  "app_name": "BrandProof AI - Standalone AI Engine",
  "version": "1.0.0",
  "ai_provider": {
    "configured": true,
    "provider": "gemini",
    "model": "gemini-2.5-flash"
  },
  "ocr_service": {
    "available": true,
    "engine": "paddleocr",
    "gpu_enabled": false
  }
}
```

---

### 2. Analyze Text
`POST /api/v1/ai/analyze-text`

Performs context-aware grammar, spelling, punctuation, and brand-guided language analysis.

#### Example Request:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/ai/analyze-text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "We is excited to announce our new prodcut launch next Tuesday! BrandFlow360 delivers unmatched results.",
    "language": "English",
    "content_type": "advertisement",
    "target_audience": "enterprise marketers",
    "instructions": "Keep the tone energetic and polished.",
    "brand_context": "Preserve the product name BrandFlow360 exactly as written."
  }'
```

#### Example Response:
```json
{
  "original_text": "We is excited to announce our new prodcut launch next Tuesday! BrandFlow360 delivers unmatched results.",
  "findings": [
    {
      "id": "finding_1",
      "category": "grammar",
      "severity": "high",
      "original_text": "We is",
      "suggestion": "We are",
      "explanation": "Subject-verb agreement error: 'We' requires the plural verb 'are'.",
      "confidence": 0.98,
      "start_offset": 0,
      "end_offset": 5
    },
    {
      "id": "finding_2",
      "category": "spelling",
      "severity": "medium",
      "original_text": "prodcut",
      "suggestion": "product",
      "explanation": "Spelling mistake in 'product'.",
      "confidence": 0.99,
      "start_offset": 34,
      "end_offset": 41
    }
  ],
  "corrected_text": "We are excited to announce our new product launch next Tuesday! BrandFlow360 delivers unmatched results.",
  "summary": {
    "total_findings": 2,
    "findings_by_category": {
      "grammar": 1,
      "spelling": 1
    },
    "findings_by_severity": {
      "high": 1,
      "medium": 1
    },
    "assessment": "Detected 2 language issues: 1 grammar subject-verb error and 1 spelling mistake. Brand name BrandFlow360 preserved."
  }
}
```

---

### 3. Extract Text from Image (OCR Only)
`POST /api/v1/ai/extract-text`

Extracts text from an image using the local OCR engine without running LLM grammar analysis.

#### Example Request:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/ai/extract-text \
  -F "file=@creative_banner.png"
```

#### Example Response:
```json
{
  "extracted_text": "Summer Sale\nUp to 50% Off On All Plans",
  "ocr_metadata": {
    "engine": "paddleocr",
    "language": "en",
    "lines_detected": 2,
    "average_confidence": 0.9654,
    "processing_time_ms": 320.15
  },
  "success": true
}
```

---

### 4. Analyze Image (OCR + Grammar Analysis)
`POST /api/v1/ai/analyze-image`

Extracts text from an image via OCR and forwards it directly through the grammar and language analysis pipeline.

#### Example Request:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/ai/analyze-image \
  -F "file=@ad_creative.png" \
  -F "content_type=social media post" \
  -F "brand_context=Preserve trademarked terms."
```

#### Example Response:
```json
{
  "extracted_text": "Get the best deal for your bussiness today!",
  "ocr_metadata": {
    "engine": "paddleocr",
    "language": "en",
    "lines_detected": 1,
    "average_confidence": 0.9712,
    "processing_time_ms": 280.45
  },
  "findings": [
    {
      "id": "finding_1",
      "category": "spelling",
      "severity": "medium",
      "original_text": "bussiness",
      "suggestion": "business",
      "explanation": "Corrected spelling of 'business'.",
      "confidence": 0.97,
      "start_offset": 27,
      "end_offset": 36
    }
  ],
  "corrected_text": "Get the best deal for your business today!",
  "summary": {
    "total_findings": 1,
    "findings_by_category": {
      "spelling": 1
    },
    "findings_by_severity": {
      "medium": 1
    },
    "assessment": "1 spelling correction applied to OCR extracted text."
  }
}
```

---

## 6. Testing

The suite contains **26 automated tests** covering all 13 required scenarios:
1. Valid text analysis
2. Correct text with no unnecessary corrections
3. Text containing grammar errors
4. Ambiguous sentence handling
5. Preservation of product names and numbers
6. Valid image OCR extraction using real PaddleOCR
7. Unreadable / corrupted images
8. Unsupported file formats
9. Oversized image uploads
10. Missing model API credentials
11. Provider timeouts and rate limits
12. Invalid structured model responses
13. Invalid API requests (blank text, missing fields, length limit, prompt injection)

To run the full test suite:

```bash
python -m pytest -v
```

---

## 7. Supabase Database Migrations

Production-ready PostgreSQL migration scripts are located in the repository under:

```text
supabase/
└── migrations/
    ├── 001_create_profiles.sql
    ├── 002_create_analysis_history.sql
    ├── 003_create_image_metadata.sql
    └── 004_disable_rls.sql
```

### Purpose of Each Migration File

| Migration File | Target Schema / Objects | Purpose & Details |
|---|---|---|
| `001_create_profiles.sql` | `public.profiles`, trigger `on_auth_user_created` | Creates user profiles referencing Supabase `auth.users(id)` with `ON DELETE CASCADE`. Implements an idempotent trigger function `handle_new_user()` using `ON CONFLICT (id) DO NOTHING` to automatically create a profile whenever a user registers. Does not store passwords. |
| `002_create_analysis_history.sql` | `public.analysis_history`, indexes | Stores marketing text and OCR image analysis results. Uses native PostgreSQL `gen_random_uuid()` for IDs. Column `user_id` is nullable to preserve the guest/unauthenticated analysis workflow. Includes check constraint `CHECK (input_type IN ('text', 'image'))` and b-tree indexes on `user_id` and `created_at DESC`. |
| `003_create_image_metadata.sql` | `public.image_metadata`, indexes | Stores S3 object keys and image file metadata (not image binary bytes). Foreign key `analysis_id` references `public.analysis_history(id)` with `ON DELETE CASCADE`. Enforces uniqueness on `object_key`. Foreign key `user_id` references `auth.users(id)` (nullable for guests). |
| `004_disable_rls.sql` | RLS status on all 3 tables | Explicitly disables Row Level Security on `public.profiles`, `public.analysis_history`, and `public.image_metadata`. This allows the backend API service to manage data via the Supabase Service Role Key without client policy interference. |

### Required Execution Order

The migrations **must be executed in numerical sequence**:

1. **`001_create_profiles.sql`** (depends on Supabase `auth.users`)
2. **`002_create_analysis_history.sql`** (independent table referencing `auth.users`)
3. **`003_create_image_metadata.sql`** (foreign key references `analysis_history(id)`)
4. **`004_disable_rls.sql`** (alters `profiles`, `analysis_history`, and `image_metadata`)

---

## 8. How to Execute Migrations in Supabase SQL Editor

Follow these exact steps to apply the schema migrations:

1. **Log in to Supabase**: Navigate to [https://supabase.com/dashboard](https://supabase.com/dashboard) and select your project.
2. **Open SQL Editor**: In the left sidebar, click the **SQL Editor** tab (icon `>_`).
3. **Run Migration 001**:
   - Click **+ New Query**.
   - Copy the entire contents of [`supabase/migrations/001_create_profiles.sql`](../supabase/migrations/001_create_profiles.sql).
   - Paste into the editor and click **Run** (or `Ctrl+Enter`). Confirm the output says `Success. No rows returned`.
4. **Run Migration 002**:
   - Click **+ New Query**.
   - Copy the contents of [`supabase/migrations/002_create_analysis_history.sql`](../supabase/migrations/002_create_analysis_history.sql).
   - Paste and click **Run**.
5. **Run Migration 003**:
   - Click **+ New Query**.
   - Copy the contents of [`supabase/migrations/003_create_image_metadata.sql`](../supabase/migrations/003_create_image_metadata.sql).
   - Paste and click **Run**.
6. **Run Migration 004**:
   - Click **+ New Query**.
   - Copy the contents of [`supabase/migrations/004_disable_rls.sql`](../supabase/migrations/004_disable_rls.sql).
   - Paste and click **Run**.

---

## 9. Verifying Tables, Constraints, and RLS

After running the migrations, execute this verification query in the Supabase SQL Editor:

```sql
-- 1. Verify all 3 tables exist
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('profiles', 'analysis_history', 'image_metadata');

-- 2. Verify Row Level Security is DISABLED
SELECT relname AS table_name, relrowsecurity AS rls_enabled 
FROM pg_class 
JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
WHERE pg_namespace.nspname = 'public' 
  AND relname IN ('profiles', 'analysis_history', 'image_metadata');
-- Expected: rls_enabled = false for all three tables.

-- 3. Verify Foreign Keys and Constraints
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'public';
```

---

## 10. S3-Compatible Image Storage & Backend Setup

### Storage Provider Architecture
The backend uses `boto3` to provide a modular storage layer supporting AWS S3, Cloudflare R2, MinIO, Wasabi, and DigitalOcean Spaces.
- **Image bytes are never stored in PostgreSQL.**
- **Presigned URLs** are generated on-demand with configurable expiration (`S3_PRESIGNED_EXPIRY_SECONDS=3600`).
- **Partial Failure Compensation:** If an S3 image upload succeeds but the subsequent PostgreSQL database insertion fails, the backend immediately rolls back and deletes the uploaded S3 object to prevent orphaned storage bloat.

### Environment Configuration Guide

Update your `.env` file with your credentials:

```env
# ==============================================================================
# 1. Single Gemini API Key (Strictly one key, no pools, no rotation)
# ==============================================================================
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# ==============================================================================
# 2. Supabase Configuration (PostgreSQL Database & Auth)
# ==============================================================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# ==============================================================================
# 3. S3-Compatible Image Storage Configuration
# ==============================================================================
S3_ENDPOINT_URL=https://s3.us-east-1.amazonaws.com # Or your R2/MinIO endpoint
S3_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_key
S3_USE_SSL=true
```

> [!CAUTION]
> **Security & Secret Protection Rules:**
> - `SUPABASE_SERVICE_ROLE_KEY`, `S3_SECRET_ACCESS_KEY`, and `GEMINI_API_KEY` must **NEVER** be committed to Git or exposed in frontend client code.
> - The `.env` file is excluded from version control via `.gitignore`.
> - The `/health` endpoint strictly reports service operational statuses and masks endpoints without revealing secret tokens.

---

## 11. Testing & Validation Status

The backend includes **38 automated tests** passing across all modules:

```bash
cd AI_Backend
python -m pytest tests/ -v
```

### Passed Automated Test Suites:
- `tests/test_sql_migrations.py`: Schema validity, PostgreSQL syntax AST parsing via `sqlglot`, execution order, constraint types, and absence of MySQL syntax.
- `tests/test_storage_service.py`: S3 upload, deletion, unique key generation, MIME type validation, file size enforcement, and presigned URLs.
- `tests/test_supabase_integration.py`: Supabase Auth registration, login, token verification, analysis history insertion, image metadata insertion, and partial-failure rollback compensation.
- `tests/test_api.py`: FastAPI endpoints (`/analyze-text`, `/analyze-image`, `/extract-text`, `/health`, auth, and history).
- `tests/test_grammar_analyzer.py`: LLM structured single-request analysis, error handling, rate limits, quota limits.
- `tests/test_ocr_service.py`: Real PaddleOCR extraction, corrupted image handling, image format support.
- `tests/test_reliability_security.py`: Input boundaries, payload size limits, prompt injection safety.

### Validation Limitations
- **Static Syntax & AST Validation:** Every SQL migration file has been statically validated against the PostgreSQL dialect with zero syntax or ordering errors.
- **Live Database Execution:** A live Supabase connection was not configured in the local development environment; therefore, live database execution against Supabase remains unverified until executed in your target project using the provided steps.

---

## 12. Known Limitations & Future Extension Points

- **OCR Scope:** Currently extracts printed text from 2D images (PNG, JPEG, WEBP, BMP, TIFF). It does not analyze logos, color palettes, visual layout compliance, or handwritten text.
- **Language Coverage:** Default OCR and grammar prompt are tuned for English. Additional languages can be enabled via `OCR_LANG` and request `language` parameters.
- **Extension Hooks:** Service interfaces in `app/services/` are modularly designed to support future additions:
  - Brand compliance checking
  - Evidence-backed claim verification (Brand Truth Graph)
  - Risk scoring and adaptive human review
  - Cross-content consistency checks
