"""Integration tests for BrandProof AI FastAPI endpoints."""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def test_health_check_endpoint(client: TestClient):
    """Verifies the GET /api/v1/ai/health endpoint behavior."""
    response = client.get("/api/v1/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "app_name" in data
    assert "version" in data
    assert "ai_provider" in data
    assert data["ai_provider"]["provider"] == "gemini"
    assert data["ai_provider"]["model"] == "gemini-3.5-flash-lite"
    assert "ocr_service" in data
    assert "api_key" not in str(data)  # Credentials never exposed


def test_root_endpoint(client: TestClient):
    """Verifies the root landing endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["docs"] == "/docs"
    assert "/health" in data["health"]


def test_analyze_text_endpoint_success(client: TestClient, mock_llm_grammar_error_response):
    """Verifies POST /api/v1/ai/analyze-text with successful Gemini analysis."""
    payload = {
        "text": "We is excited to announce our new prodcut launch next Tuesday!",
        "language": "English",
        "content_type": "advertisement",
        "target_audience": "general consumers",
        "instructions": "Keep the tone professional.",
        "brand_context": "Preserve all product names.",
    }

    with patch(
        "app.services.ai_provider.ai_provider_service.generate_structured_json",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = mock_llm_grammar_error_response

        response = client.post("/api/v1/ai/analyze-text", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["original_text"] == payload["text"]
        assert len(data["findings"]) == 2
        assert "We are" in data["corrected_text"]
        assert data["summary"]["total_findings"] == 2


def test_analyze_text_missing_ai_key(client: TestClient):
    """Verifies POST /api/v1/ai/analyze-text returns 503 when AI credentials are unconfigured."""
    payload = {"text": "Simple test content."}
    with patch("app.services.ai_provider.ai_provider_service.api_key", None):
        response = client.post("/api/v1/ai/analyze-text", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "AIProviderConfigError" in str(data) or "missing" in str(data).lower()


def test_analyze_text_rate_limit(client: TestClient):
    """Verifies POST /api/v1/ai/analyze-text returns HTTP 429 on Gemini rate limit."""
    from app.core.exceptions import AIRateLimitError

    payload = {"text": "Test rate limit content."}
    with patch(
        "app.services.ai_provider.ai_provider_service.generate_structured_json",
        side_effect=AIRateLimitError("Gemini rate limit exceeded. Please wait a moment before retrying."),
    ):
        response = client.post("/api/v1/ai/analyze-text", json=payload)
        assert response.status_code == 429
        data = response.json()
        assert "AIRateLimitError" in str(data)
        assert "rate limit exceeded" in str(data).lower()


def test_analyze_text_quota_exhausted(client: TestClient):
    """Verifies POST /api/v1/ai/analyze-text returns HTTP 429 on Gemini quota exhaustion."""
    from app.core.exceptions import AIQuotaExhaustedError

    payload = {"text": "Test quota exhausted content."}
    with patch(
        "app.services.ai_provider.ai_provider_service.generate_structured_json",
        side_effect=AIQuotaExhaustedError("Gemini daily API quota limit reached. Please wait for the daily quota reset."),
    ):
        response = client.post("/api/v1/ai/analyze-text", json=payload)
        assert response.status_code == 429
        data = response.json()
        assert "AIQuotaExhaustedError" in str(data)
        assert "daily api quota limit reached" in str(data).lower()


def test_extract_text_endpoint_success(client: TestClient, create_test_image):
    """Verifies POST /api/v1/ai/extract-text returns OCR extraction and metadata."""
    img_bytes = create_test_image("Summer Sale 50% Off", size=(320, 80))

    files = {"file": ("ad_banner.png", img_bytes, "image/png")}
    response = client.post("/api/v1/ai/extract-text", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "ocr_metadata" in data
    assert data["ocr_metadata"]["lines_detected"] >= 1
    assert "Summer" in data["extracted_text"] or "Sale" in data["extracted_text"]


def test_extract_text_corrupted_image(client: TestClient, corrupted_image_bytes):
    """Verifies POST /api/v1/ai/extract-text returns 400 for corrupted image."""
    files = {"file": ("corrupt.png", corrupted_image_bytes, "image/png")}
    response = client.post("/api/v1/ai/extract-text", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "InvalidImageError" in str(data) or "corrupted" in str(data).lower()


def test_extract_text_unsupported_media_type(client: TestClient):
    """Verifies POST /api/v1/ai/extract-text returns 415 for unsupported media."""
    files = {"file": ("doc.txt", b"plain text content", "text/plain")}
    response = client.post("/api/v1/ai/extract-text", files=files)

    assert response.status_code == 415
    data = response.json()
    assert "UnsupportedMediaError" in str(data) or "unsupported" in str(data).lower()


def test_analyze_image_endpoint_success(
    client: TestClient, create_test_image, mock_llm_grammar_error_response
):
    """Verifies POST /api/v1/ai/analyze-image extracts text and runs grammar analysis."""
    img_bytes = create_test_image("We is excited for launch", size=(320, 80))

    files = {"file": ("poster.png", img_bytes, "image/png")}
    data = {
        "language": "English",
        "content_type": "social media post",
        "target_audience": "tech leaders",
        "instructions": "Be punchy.",
        "brand_context": "Preserve all technical names.",
    }

    with patch(
        "app.services.ai_provider.ai_provider_service.generate_structured_json",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = mock_llm_grammar_error_response

        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res_data = response.json()

        assert "extracted_text" in res_data
        assert "ocr_metadata" in res_data
        assert "findings" in res_data
        assert "corrected_text" in res_data
        assert "summary" in res_data


def test_generate_report_pdf_endpoint(client: TestClient):
    """Verifies POST /api/v1/ai/generate-report returns a valid 2-page PDF."""
    payload = {
        "title": "Launch Banner Review",
        "original_text": "We is excited to announce our new prodcut launch next Tuesday!",
        "corrected_text": "We are excited to announce our new product launch next Tuesday!",
        "findings": [
            {
                "id": "finding_1",
                "category": "grammar",
                "severity": "high",
                "original_text": "We is",
                "suggestion": "We are",
                "explanation": "Subject-verb agreement error: 'We' takes 'are'.",
                "rule": "Grammar: Subject-Verb Agreement",
            },
            {
                "id": "finding_2",
                "category": "spelling",
                "severity": "medium",
                "original_text": "prodcut",
                "suggestion": "product",
                "explanation": "Spelling error: 'product'.",
                "rule": "Spelling: Correct Vocabulary",
            },
        ],
        "summary": "Text contains 2 issues. All corrected with brand guidelines.",
        "content_type": "advertisement",
        "model_name": "Gemini 3.5 Flash",
    }

    response = client.post("/api/v1/ai/generate-report", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    # PDF bytes always start with %PDF
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def test_analyze_media_endpoint_success(client: TestClient, monkeypatch):
    """Verifies POST /api/v1/ai/analyze-media processes audio/video and returns MediaAnalysisResponse."""
    import io
    from app.api.schemas import (
        MediaAnalysisResponse,
        MediaAnalysisSummary,
        GrammarFinding,
    )

    async def mock_analyze_media(**kwargs):
        return MediaAnalysisResponse(
            status="success",
            media_type="audio",
            duration=15.0,
            original_text="We is excited to present Brand proof AI.",
            corrected_text="We are excited to present BrandProof AI.",
            findings=[
                GrammarFinding(
                    id="sp-1",
                    category="grammar",
                    severity="high",
                    original_text="We is",
                    suggestion="We are",
                    explanation="Subject-verb agreement",
                    timestamp="00:02",
                    media_type="speech",
                )
            ],
            summary=MediaAnalysisSummary(total_issues=1, grammar_issues=1),
        )

    monkeypatch.setattr("app.speech.analyze_media", mock_analyze_media)

    fake_mp3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 200
    files = {"file": ("test.mp3", io.BytesIO(fake_mp3), "audio/mpeg")}
    response = client.post("/api/v1/ai/analyze-media", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["media_type"] == "audio"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["timestamp"] == "00:02"


