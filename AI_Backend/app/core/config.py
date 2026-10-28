"""Configuration management for BrandProof AI Engine using Pydantic Settings."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "BrandProof AI - Standalone AI Engine"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1/ai"
    ENVIRONMENT: str = "development"

    # Single Gemini API Key & Model Configuration
    # Strictly one key, no key rotation, no key pools, no fallback keys
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Optional alias for backward compatibility
    AI_API_KEY: Optional[str] = None
    AI_MODEL: Optional[str] = None
    AI_PROVIDER: str = "gemini"
    AI_BASE_URL: Optional[str] = None

    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_RETRIES: int = 2

    # Processing limits & Security
    MAX_UPLOAD_SIZE_MB: int = 10
    MAX_TEXT_LENGTH: int = 50000
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
        "image/tiff",
    ]

    # OCR settings
    OCR_ENGINE: str = "paddleocr"
    OCR_LANG: str = "en"
    OCR_USE_GPU: bool = False
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK: str = "True"

    @property
    def effective_api_key(self) -> Optional[str]:
        """Returns the single configured Gemini API key."""
        key = self.GEMINI_API_KEY or self.AI_API_KEY
        return key.strip() if key else None

    @property
    def effective_model(self) -> str:
        """Returns the active Gemini model identifier."""
        return self.GEMINI_MODEL or self.AI_MODEL or "gemini-3.5-flash-lite"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.effective_api_key)


# Hardened environment flags
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")

settings = Settings()
