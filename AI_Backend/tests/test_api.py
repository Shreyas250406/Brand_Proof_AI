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
