"""API route definitions for BrandProof AI Engine."""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from app.api.schemas import (
    TextAnalysisRequest,
    TextAnalysisResponse,
    ImageAnalysisResponse,
    ExtractTextResponse,
    HealthResponse,
    AIProviderHealth,
    OCRServiceHealth,
    ErrorResponse,
)
from app.core.config import settings
from app.core.exceptions import (
    BrandProofAIException,
    AIProviderConfigError,
    AIProviderTimeoutError,
    AIProviderResponseError,
    AIProviderError,
    AIRateLimitError,
    AIQuotaExhaustedError,
    OCRProcessingError,
    InvalidImageError,
    PayloadTooLargeError,
    UnsupportedMediaError,
)
from app.services.text_processor import text_processor_service
from app.services.ai_provider import ai_provider_service
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI Engine"])


@router.post(
    "/analyze-text",
    response_model=TextAnalysisResponse,
    summary="Analyze marketing text for grammar, language quality, and brand alignment",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input text or formatting"},
        413: {"model": ErrorResponse, "description": "Text length exceeds maximum allowed limit"},
        502: {"model": ErrorResponse, "description": "AI provider service error"},
        503: {"model": ErrorResponse, "description": "AI provider not configured"},
        504: {"model": ErrorResponse, "description": "AI provider request timed out"},
    },
)
async def analyze_text(request: TextAnalysisRequest) -> TextAnalysisResponse:
    """Accepts marketing text and performs dynamic, context-aware grammar, spelling,

    clarity, and brand-guided analysis using the configured LLM.
    """
    try:
        return await text_processor_service.process_text_analysis(request)
    except (AIRateLimitError, AIQuotaExhaustedError) as exc:
        logger.warning("Gemini rate/quota limit: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_type": type(exc).__name__, "message": exc.message},
        )
    except AIProviderConfigError as exc:
        logger.error("AI provider configuration error: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "AIProviderConfigError", "message": exc.message},
        )
    except AIProviderTimeoutError as exc:
        logger.error("AI provider timeout: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error_type": "AIProviderTimeoutError", "message": exc.message},
        )
    except (AIProviderResponseError, AIProviderError) as exc:
        logger.error("AI provider error: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_type": type(exc).__name__, "message": exc.message},
        )
    except PayloadTooLargeError as exc:
        logger.warning("Payload too large: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error_type": "PayloadTooLargeError", "message": exc.message},
        )
    except Exception as exc:
        logger.exception("Unexpected error analyzing text")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Analysis failed: {str(exc)}"},
        )


@router.post(
    "/extract-text",
    response_model=ExtractTextResponse,
    summary="Extract text and metadata from an image using OCR without grammar analysis",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or corrupted image"},
        413: {"model": ErrorResponse, "description": "Image file size exceeds allowed limit"},
        415: {"model": ErrorResponse, "description": "Unsupported image format"},
        502: {"model": ErrorResponse, "description": "OCR extraction failure"},
    },
)
async def extract_text(
    file: UploadFile = File(..., description="Image file (PNG, JPG, WEBP, BMP, TIFF)"),
) -> ExtractTextResponse:
    """Extracts text from an uploaded image using the local OCR engine."""
    try:
        image_bytes = await file.read()
        extracted_text, metadata = text_processor_service.process_image_extraction(
            image_bytes=image_bytes,
            content_type=file.content_type,
            filename=file.filename,
        )
        return ExtractTextResponse(
            extracted_text=extracted_text,
            ocr_metadata=metadata,
            success=True,
        )
    except InvalidImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_type": "InvalidImageError", "message": exc.message},
        )
    except PayloadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error_type": "PayloadTooLargeError", "message": exc.message},
        )
    except UnsupportedMediaError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error_type": "UnsupportedMediaError", "message": exc.message},
        )
    except OCRProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_type": "OCRProcessingError", "message": exc.message},
        )
    except Exception as exc:
        logger.exception("Unexpected error extracting text from image")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Extraction failed: {str(exc)}"},
        )


@router.post(
    "/analyze-image",
    response_model=ImageAnalysisResponse,
    summary="Extract text from an image and run complete grammar analysis pipeline",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or corrupted image"},
        413: {"model": ErrorResponse, "description": "Image file size exceeds allowed limit"},
        415: {"model": ErrorResponse, "description": "Unsupported image format"},
        502: {"model": ErrorResponse, "description": "OCR or AI provider error"},
        503: {"model": ErrorResponse, "description": "AI provider not configured"},
        504: {"model": ErrorResponse, "description": "AI provider request timed out"},
    },
)
async def analyze_image(
    file: UploadFile = File(..., description="Image file containing marketing copy"),
    language: Optional[str] = Form("English"),
    content_type: Optional[str] = Form(None),
    target_audience: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    brand_context: Optional[str] = Form(None),
) -> ImageAnalysisResponse:
    """Extracts text from an image via OCR, then runs full grammar, spelling, and

    clarity analysis with context-aware suggestions.
    """
    try:
        image_bytes = await file.read()
        return await text_processor_service.process_image_analysis(
            image_bytes=image_bytes,
            content_type=file.content_type,
            filename=file.filename,
            language=language,
            analysis_content_type=content_type,
            target_audience=target_audience,
            instructions=instructions,
            brand_context=brand_context,
        )
    except InvalidImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_type": "InvalidImageError", "message": exc.message},
        )
    except PayloadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error_type": "PayloadTooLargeError", "message": exc.message},
        )
    except UnsupportedMediaError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error_type": "UnsupportedMediaError", "message": exc.message},
        )
    except OCRProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_type": "OCRProcessingError", "message": exc.message},
        )
    except (AIRateLimitError, AIQuotaExhaustedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_type": type(exc).__name__, "message": exc.message},
        )
    except AIProviderConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "AIProviderConfigError", "message": exc.message},
        )
    except AIProviderTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error_type": "AIProviderTimeoutError", "message": exc.message},
        )
    except (AIProviderResponseError, AIProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_type": type(exc).__name__, "message": exc.message},
        )
    except Exception as exc:
        logger.exception("Unexpected error in image analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Image analysis failed: {str(exc)}"},
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Get service health, AI provider status, and OCR engine availability",
)
async def health_check() -> HealthResponse:
    """Returns the operational status of the engine.

    Never exposes API keys or secrets.
    """
    ai_configured = ai_provider_service.is_configured()
    ocr_available = ocr_service.is_available()

    status_str = "healthy" if (ai_configured and ocr_available) else "degraded"

    return HealthResponse(
        status=status_str,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        ai_provider=AIProviderHealth(
            configured=ai_configured,
            provider="gemini",
            model=settings.effective_model,
        ),
        ocr_service=OCRServiceHealth(
            available=ocr_available,
            engine=settings.OCR_ENGINE,
            gpu_enabled=settings.OCR_USE_GPU,
        ),
    )
