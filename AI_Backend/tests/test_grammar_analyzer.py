"""Unit tests for Grammar Analyzer and Gemini AI Provider layers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.grammar_analyzer import GrammarAnalyzerService
from app.services.ai_provider import AIProviderService
from app.core.exceptions import (
    AIProviderConfigError,
    AIProviderTimeoutError,
    AIProviderError,
    AIProviderResponseError,
)


@pytest.mark.asyncio
async def test_valid_text_analysis(mock_llm_grammar_error_response):
    """Scenario 1 & 3: Valid text analysis with grammar and spelling findings."""
    mock_provider = MagicMock(spec=AIProviderService)
    mock_provider.generate_structured_json = AsyncMock(
        return_value=mock_llm_grammar_error_response
    )

    analyzer = GrammarAnalyzerService(ai_provider=mock_provider)
    input_text = "We is excited to announce our new prodcut launch next Tuesday!"

    response = await analyzer.analyze(
        text=input_text,
        content_type="advertisement",
        target_audience="general consumers",
    )

    assert response.original_text == input_text
    assert len(response.findings) == 2
    assert response.corrected_text == "We are excited to announce our new product launch next Tuesday!"

    finding_1 = response.findings[0]
    assert finding_1.category == "grammar"
    assert finding_1.severity == "high"
    assert finding_1.original_text == "We is"
    assert finding_1.suggestion == "We are"
    assert finding_1.start_offset == 0
    assert finding_1.end_offset == 5

    assert response.summary.total_findings == 2
    assert response.summary.findings_by_category["grammar"] == 1
    assert response.summary.findings_by_category["spelling"] == 1
    assert response.summary.findings_by_severity["high"] == 1


@pytest.mark.asyncio
async def test_correct_text_no_unnecessary_corrections(mock_llm_clean_text_response):
    """Scenario 2: Correct text with no unnecessary corrections."""
    mock_provider = MagicMock(spec=AIProviderService)
    mock_provider.generate_structured_json = AsyncMock(
        return_value=mock_llm_clean_text_response
    )

    analyzer = GrammarAnalyzerService(ai_provider=mock_provider)
    input_text = "Our award-winning platform accelerates compliance review by 80%."

    response = await analyzer.analyze(text=input_text)

    assert response.original_text == input_text
    assert len(response.findings) == 0
    assert response.corrected_text == input_text
    assert response.summary.total_findings == 0
    assert "no grammatical" in response.summary.assessment.lower() or len(response.findings) == 0


@pytest.mark.asyncio
async def test_ambiguous_sentence_handling(mock_llm_ambiguous_text_response):
    """Scenario 4: Ambiguous sentences explained without inventing arbitrary meaning."""
    mock_provider = MagicMock(spec=AIProviderService)
    mock_provider.generate_structured_json = AsyncMock(
        return_value=mock_llm_ambiguous_text_response
    )

    analyzer = GrammarAnalyzerService(ai_provider=mock_provider)
    input_text = "The manager told the designer he made a mistake."

    response = await analyzer.analyze(text=input_text)

    assert len(response.findings) == 1
    finding = response.findings[0]
    assert finding.category == "clarity"
    assert "ambiguous" in finding.explanation.lower()
    assert finding.original_text == input_text


@pytest.mark.asyncio
async def test_preservation_of_product_names_and_numbers(mock_llm_brand_preservation_response):
    """Scenario 5: Preservation of product names and numbers with brand context."""
    mock_provider = MagicMock(spec=AIProviderService)
    mock_provider.generate_structured_json = AsyncMock(
        return_value=mock_llm_brand_preservation_response
    )

    analyzer = GrammarAnalyzerService(ai_provider=mock_provider)
    input_text = "BrandFlow360 v2.5 has launched with 10 new features."

    response = await analyzer.analyze(
        text=input_text,
        brand_context="BrandFlow360 is our registered trademark. Do not change casing or spelling.",
    )

    assert "BrandFlow360" in response.corrected_text
    assert "v2.5" in response.corrected_text
    assert "10" in response.corrected_text


@pytest.mark.asyncio
async def test_missing_model_credentials():
    """Scenario 10: Missing model API credentials raises AIProviderConfigError."""
    # AIProviderService initialized with explicit empty api_key
    provider = AIProviderService(api_key="")
    with pytest.raises(AIProviderConfigError) as exc_info:
        await provider.generate_structured_json(
            system_prompt="Test",
            user_prompt="Test",
        )
    assert "missing" in str(exc_info.value).lower() or "gemini api key" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_provider_timeout_and_errors():
    """Scenario 11: Provider timeouts and API errors raised explicitly."""
    import httpx

    provider = AIProviderService(api_key="test_key", max_retries=0)

    # Test Timeout
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(AIProviderTimeoutError) as exc_info:
            await provider.generate_structured_json(
                system_prompt="Test",
                user_prompt="Test",
            )
        assert "timed out" in str(exc_info.value).lower()

    # Test Generic API Error (HTTP 500)
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate_structured_json(
                system_prompt="Test",
                user_prompt="Test",
            )
        assert "500" in str(exc_info.value) or "internal server error" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_provider_rate_limit_and_quota_errors():
    """Verifies that HTTP 429 rate limits and daily quota exhaustion are distinguished."""
    from app.core.exceptions import AIRateLimitError, AIQuotaExhaustedError

    provider = AIProviderService(api_key="test_key", max_retries=0)

    # Test Transient Rate Limit (429)
    rate_limit_resp = MagicMock()
    rate_limit_resp.status_code = 429
    rate_limit_resp.text = '{"error":{"code":429,"message":"Queries per minute quota exceeded","status":"RESOURCE_EXHAUSTED"}}'
    rate_limit_resp.headers = {"Retry-After": "2"}
    rate_limit_resp.json.return_value = {"error": {"code": 429, "message": "Queries per minute quota exceeded"}}

    with patch("httpx.AsyncClient.post", return_value=rate_limit_resp):
        with pytest.raises(AIRateLimitError) as exc_info:
            await provider.generate_structured_json(
                system_prompt="Test",
                user_prompt="Test",
            )
        assert "rate limit exceeded" in str(exc_info.value).lower()

    # Test Daily Quota Exhaustion (429)
    quota_resp = MagicMock()
    quota_resp.status_code = 429
    quota_resp.text = '{"error":{"code":429,"message":"Daily quota exceeded for Free Tier","status":"RESOURCE_EXHAUSTED"}}'
    quota_resp.headers = {}
    quota_resp.json.return_value = {"error": {"code": 429, "message": "Daily quota exceeded for Free Tier"}}

    with patch("httpx.AsyncClient.post", return_value=quota_resp):
        with pytest.raises(AIQuotaExhaustedError) as exc_info:
            await provider.generate_structured_json(
                system_prompt="Test",
                user_prompt="Test",
            )
        assert "daily api quota limit reached" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_invalid_structured_model_response():
    """Scenario 12: Invalid structured model response raises AIProviderResponseError."""
    mock_provider = MagicMock(spec=AIProviderService)
    # Returns non-dict
    mock_provider.generate_structured_json = AsyncMock(
        return_value="this is not a dictionary"
    )

    analyzer = GrammarAnalyzerService(ai_provider=mock_provider)

    with pytest.raises(AIProviderResponseError) as exc_info:
        await analyzer.analyze(text="Hello world")
    assert "not a json object" in str(exc_info.value).lower()
