"""AI Provider service strictly managing a single Gemini API key with bounded retries."""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings
from app.core.exceptions import (
    AIProviderError,
    AIProviderConfigError,
    AIProviderTimeoutError,
    AIProviderResponseError,
    AIRateLimitError,
    AIQuotaExhaustedError,
)

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class AIProviderService:
    """Manages Gemini API requests using strictly ONE configured API key.

    Enforces:
    - Exactly one API key loaded from environment.
    - No key rotation, key pools, or fallback keys.
    - Single request per submission (minimizing requests and tokens).
    - Graceful handling of rate limits (HTTP 429) and quota exhaustion.
    - Bounded exponential backoff retries respecting API retry delay.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        # Single key only: strictly no fallback keys or key pools
        self.api_key = api_key if api_key is not None else settings.effective_api_key
        self.model = model or settings.effective_model
        self.timeout = timeout or settings.AI_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

    def is_configured(self) -> bool:
        """Checks if the single Gemini API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def _parse_retry_delay(self, response: httpx.Response, attempt: int) -> float:
        """Extracts retry delay from Retry-After header or Gemini error body,

        with bounded exponential backoff fallback.
        """
        # Check standard Retry-After header
        retry_header = response.headers.get("Retry-After")
        if retry_header:
            try:
                delay = float(retry_header)
                return min(delay, 10.0)
            except ValueError:
                pass

        # Check Gemini body details for retryDelay e.g. "2.5s" or "3s"
        try:
            body = response.json()
            error_details = body.get("error", {}).get("details", [])
            for item in error_details:
                if isinstance(item, dict) and "retryDelay" in item:
                    delay_str = str(item["retryDelay"])
                    match = re.search(r"(\d+(\.\d+)?)", delay_str)
                    if match:
                        delay = float(match.group(1))
                        return min(delay, 10.0)
        except Exception:
            pass

        # Exponential backoff bounded fallback: 1.5s, 3.0s
        return min((1.5 ** attempt) + 0.5, 8.0)

    def _is_daily_quota_exhausted(self, response_text: str) -> bool:
        """Detects whether an HTTP 429 error is due to daily quota exhaustion

        rather than a transient per-minute rate limit.
        """
        text_lower = response_text.lower()
        if "per day" in text_lower or "daily" in text_lower or "free_tier" in text_lower:
            return True
        if "quota exceeded" in text_lower and "queries per minute" not in text_lower:
            return True
        return False

    async def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Calls Gemini generateContent endpoint with strictly one key and structured output.

        Combines all checks (grammar, spelling, tone, clarity, explanations,
        and corrected text) into exactly ONE request per submission.
        """
        if not self.is_configured():
            raise AIProviderConfigError(
                "Gemini API key is missing. Please set GEMINI_API_KEY in your .env file."
            )

        url = f"{GEMINI_BASE_URL}/{self.model}:generateContent"
        params = {"key": self.api_key}

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            }
        }

        # Bounded retries loop (max_retries attempts only, no infinite retry)
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, params=params, json=payload)

                # HTTP 200: Successful generation
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise AIProviderResponseError(
                            "Gemini returned no candidates in response (possible safety block)."
                        )

                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise AIProviderResponseError("Gemini returned empty content parts.")

                    raw_text = parts[0].get("text", "")
                    if not raw_text or not raw_text.strip():
                        raise AIProviderResponseError("Gemini returned empty text completion.")

                    try:
                        return json.loads(raw_text)
                    except json.JSONDecodeError as exc:
                        logger.error("Failed to parse JSON from Gemini response: %s", raw_text[:200])
                        raise AIProviderResponseError(
                            f"Gemini returned invalid JSON: {str(exc)}",
                            details={"raw_snippet": raw_text[:200]},
                        )

                # HTTP 429: Rate limit or Quota exhaustion
                if response.status_code == 429:
                    resp_text = response.text
                    logger.warning("Gemini returned HTTP 429 (attempt %d/%d): %s", attempt + 1, self.max_retries + 1, resp_text[:200])

                    # Check if daily quota is exhausted
                    if self._is_daily_quota_exhausted(resp_text):
                        raise AIQuotaExhaustedError(
                            "Gemini daily API quota limit reached. Please wait for the daily quota reset."
                        )

                    # Transient rate limit: bounded retry if attempts remain
                    if attempt < self.max_retries:
                        delay = self._parse_retry_delay(response, attempt + 1)
                        logger.info("Applying bounded backoff retry for Gemini rate limit: sleeping %.2fs", delay)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise AIRateLimitError(
                            "Gemini rate limit exceeded. Please wait a moment before sending another request."
                        )

                # HTTP 401 / 403: Authentication failure
                if response.status_code in (401, 403):
                    raise AIProviderConfigError(
                        "Gemini authentication failed: Invalid GEMINI_API_KEY."
                    )

                # HTTP 404: Invalid model identifier
                if response.status_code == 404:
                    raise AIProviderConfigError(
                        f"Configured Gemini model '{self.model}' not found or not supported for your key."
                    )

                # HTTP 503: Transient server unavailability
                if response.status_code == 503:
                    if attempt < self.max_retries:
                        delay = min((2.0 ** attempt), 6.0)
                        logger.warning("Gemini 503 Service Unavailable; retrying in %.1fs", delay)
                        await asyncio.sleep(delay)
                        continue
                    raise AIProviderError("Gemini service temporarily unavailable (503).")

                # Other HTTP errors
                raise AIProviderError(
                    f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}"
                )

            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    logger.warning("Gemini request timed out on attempt %d; retrying...", attempt + 1)
                    await asyncio.sleep(1.0)
                    continue
                raise AIProviderTimeoutError(
                    f"Request to Gemini API timed out after {self.timeout}s."
                )

            except (AIRateLimitError, AIQuotaExhaustedError, AIProviderConfigError, AIProviderTimeoutError, AIProviderResponseError):
                raise

            except Exception as exc:
                if isinstance(exc, AIProviderError):
                    raise
                logger.exception("Unexpected error communicating with Gemini API")
                raise AIProviderError(f"Unexpected error communicating with Gemini API: {str(exc)}")


# Default singleton instance
ai_provider_service = AIProviderService()
