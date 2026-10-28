"""Custom exceptions for BrandProof AI engine."""

from typing import Optional, Any, Dict


class BrandProofAIException(Exception):
    """Base exception for all BrandProof AI engine errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AIProviderConfigError(BrandProofAIException):
    """Raised when an AI provider is missing configuration or credentials."""
    pass


class AIProviderError(BrandProofAIException):
    """Raised when the AI provider returns an error or fails unexpectedly."""
    pass


class AIProviderTimeoutError(AIProviderError):
    """Raised when an AI provider request times out."""
    pass


class AIRateLimitError(AIProviderError):
    """Raised when Gemini rate limit (HTTP 429) is encountered."""
    pass


class AIQuotaExhaustedError(AIProviderError):
    """Raised when the Gemini daily quota has been exhausted."""
    pass


class AIProviderResponseError(AIProviderError):
    """Raised when the AI provider returns an unparseable or invalid response."""
    pass


class OCRProcessingError(BrandProofAIException):
    """Raised when OCR extraction fails on an image."""
    pass


class InvalidImageError(BrandProofAIException):
    """Raised when the uploaded image is corrupted or unsupported."""
    pass


class PayloadTooLargeError(BrandProofAIException):
    """Raised when the input text or file exceeds allowed limits."""
    pass


class UnsupportedMediaError(BrandProofAIException):
    """Raised when uploaded file mime type is not supported."""
    pass
