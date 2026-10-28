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
- **OCR Engine:** PaddleOCR 3.x with PaddlePaddle backend
- **Image Processing:** Pillow, OpenCV

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

## 7. Known Limitations & Future Extension Points

- **OCR Scope:** Currently extracts printed text from 2D images (PNG, JPEG, WEBP, BMP, TIFF). It does not analyze logos, color palettes, visual layout compliance, or handwritten text.
- **Language Coverage:** Default OCR and grammar prompt are tuned for English. Additional languages can be enabled via `OCR_LANG` and request `language` parameters.
- **Extension Hooks:** Service interfaces in `app/services/` are modularly designed to support future additions:
  - Brand compliance checking
  - Evidence-backed claim verification (Brand Truth Graph)
  - Risk scoring and adaptive human review
  - Cross-content consistency checks
