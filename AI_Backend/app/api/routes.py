"""API route definitions for BrandProof AI Engine."""

import re
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, Header, Query, HTTPException, status, Response
from app.api.schemas import (
    TextAnalysisRequest,
    TextAnalysisResponse,
    ImageAnalysisResponse,
    ExtractTextResponse,
    HealthResponse,
    AIProviderHealth,
    OCRServiceHealth,
    DatabaseHealth,
    StorageHealth,
    ErrorResponse,
    UserRegisterRequest,
    UserLoginRequest,
    AuthResponse,
    UserSessionResponse,
    ImageMetadataResponse,
    AnalysisHistoryItem,
    UpdateHistoryRequest,
    HistoryListResponse,
    GrammarFinding,
    AnalysisSummary,
    ReportGenerationRequest,
)
from app.core.config import settings
from app.core.exceptions import (
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
    StorageUploadError,
    DatabaseError,
    AuthenticationError,
)
from app.services.text_processor import text_processor_service
from app.services.ai_provider import ai_provider_service
from app.services.ocr_service import ocr_service
from app.services.storage_service import storage_service, StoredImageMetadata
from app.services.supabase_service import supabase_service
from app.services.report_generator import report_generator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI Engine"])


# ------------------------------------------------------------------------------
# Authentication Helpers
# ------------------------------------------------------------------------------

async def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Extracts and verifies the authenticated user from the Authorization Bearer header.
    
    Returns None for guest/unauthenticated requests without raising an error.
    """
    if not authorization or not authorization.strip():
        return None

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    if not supabase_service.is_configured():
        return None

    try:
        return await supabase_service.verify_session(token)
    except AuthenticationError as exc:
        logger.warning("Optional session check invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected error during optional session verification: %s", exc)
        return None


async def get_current_user_required(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Strictly requires an authenticated session via Authorization Bearer header."""
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_type": "AuthenticationError", "message": "Missing Authorization header."},
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_type": "AuthenticationError", "message": "Invalid Authorization header format. Expected 'Bearer <token>'."},
        )

    token = parts[1]
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase authentication is not configured."},
        )

    try:
        return await supabase_service.verify_session(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_type": "AuthenticationError", "message": exc.message},
        )
    except Exception as exc:
        logger.exception("Unexpected error during session verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Verification error: {str(exc)}"},
        )


# ------------------------------------------------------------------------------
# Authentication Endpoints
# ------------------------------------------------------------------------------

@router.post(
    "/auth/register",
    response_model=AuthResponse,
    summary="Register a new user via Supabase Auth",
)
async def register(request: UserRegisterRequest) -> AuthResponse:
    """Registers a new user account with Supabase Auth."""
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase authentication is not configured."},
        )
    try:
        res = await supabase_service.register_user(
            email=request.email.strip(),
            password=request.password,
            display_name=request.display_name.strip() if request.display_name else None,
        )
        return AuthResponse(**res)
    except AuthenticationError as exc:
        status_code = status.HTTP_409_CONFLICT if "already exists" in exc.message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail={"error_type": "AuthenticationError", "message": exc.message},
        )
    except Exception as exc:
        logger.exception("Unexpected error in register endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Registration failed: {str(exc)}"},
        )


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Authenticate a user and retrieve JWT session tokens",
)
async def login(request: UserLoginRequest) -> AuthResponse:
    """Authenticates a user via Supabase Auth."""
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase authentication is not configured."},
        )
    try:
        res = await supabase_service.login_user(
            email=request.email.strip(),
            password=request.password,
        )
        return AuthResponse(**res)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_type": "AuthenticationError", "message": exc.message},
        )
    except Exception as exc:
        logger.exception("Unexpected error in login endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Login failed: {str(exc)}"},
        )


@router.post(
    "/auth/logout",
    summary="Invalidate user session",
)
async def logout(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Signs out a user from their active Supabase session."""
    token = ""
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if supabase_service.is_configured() and token:
        await supabase_service.logout_user(token)

    return {"message": "Logged out successfully."}


@router.get(
    "/auth/me",
    response_model=UserSessionResponse,
    summary="Retrieve details of currently authenticated user session",
)
async def get_me(authorization: Optional[str] = Header(None)) -> UserSessionResponse:
    """Verifies the bearer session token and returns current user info."""
    user = await get_current_user_required(authorization)
    return UserSessionResponse(
        user_id=user["user_id"],
        email=user["email"],
        display_name=user.get("display_name"),
    )


# ------------------------------------------------------------------------------
# Core AI Analysis Endpoints
# ------------------------------------------------------------------------------

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
async def analyze_text(
    request: TextAnalysisRequest,
    authorization: Optional[str] = Header(None),
    save_history: bool = Query(True, description="Save result to analysis_history if database is configured"),
) -> TextAnalysisResponse:
    """Accepts marketing text and performs dynamic, context-aware grammar, spelling,

    clarity, and brand-guided analysis using the configured LLM.
    Optionally persists the result to Supabase analysis_history.
    """
    try:
        user = await get_current_user_optional(authorization)
        user_id = user["user_id"] if user else None

        result = await text_processor_service.process_text_analysis(request)

        # Persist to Supabase if configured and requested
        if save_history and supabase_service.is_configured():
            try:
                findings_data = [f.model_dump() for f in result.findings]
                history_record = supabase_service.save_analysis_history(
                    input_type="text",
                    original_text=result.original_text,
                    corrected_text=result.corrected_text,
                    findings=findings_data,
                    summary=result.summary.assessment,
                    model_name=settings.effective_model,
                    user_id=user_id,
                )
                result.id = history_record.get("id")
                result.created_at = str(history_record.get("created_at", ""))
            except Exception as db_exc:
                logger.error("Failed to persist text analysis history: %s", db_exc)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"error_type": "DatabaseError", "message": f"Database persistence failed: {str(db_exc)}"},
                )

        return result

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
    summary="Extract text from image via OCR, upload to S3, run grammar analysis, and record history",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or corrupted image"},
        413: {"model": ErrorResponse, "description": "Image file size exceeds allowed limit"},
        415: {"model": ErrorResponse, "description": "Unsupported image format"},
        502: {"model": ErrorResponse, "description": "OCR, S3 storage, or AI provider error"},
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
    save_storage: bool = Form(True, description="Upload and persist image in S3-compatible storage"),
    save_history: bool = Form(True, description="Persist analysis history and image metadata to Supabase"),
    authorization: Optional[str] = Header(None),
) -> ImageAnalysisResponse:
    """Executes the full image workflow:

    1. Validates input image.
    2. Performs OCR extraction using local OCR engine (no Gemini OCR).
    3. Analyzes extracted text via single Gemini call.
    4. Uploads image to S3-compatible storage if persistence is enabled.
    5. Saves analysis result to analysis_history in Supabase.
    6. Saves image metadata to image_metadata linked to analysis_history.
    7. Compensates partial failures: rolls back S3 upload if database insert fails.
    8. Returns analysis results and presigned image retrieval URL.
    """
    image_bytes = await file.read()
    user = await get_current_user_optional(authorization)
    user_id = user["user_id"] if user else None

    # Step 1: Validate image format and limits
    try:
        storage_service.validate_image(image_bytes, file.content_type)
    except (InvalidImageError, PayloadTooLargeError, UnsupportedMediaError) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                if isinstance(exc, PayloadTooLargeError)
                else (
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                    if isinstance(exc, UnsupportedMediaError)
                    else status.HTTP_400_BAD_REQUEST
                )
            ),
            detail={"error_type": type(exc).__name__, "message": exc.message},
        )

    # Step 2: Extract text using existing local OCR service
    try:
        extracted_text, ocr_metadata = text_processor_service.process_image_extraction(
            image_bytes=image_bytes,
            content_type=file.content_type,
            filename=file.filename,
        )
    except OCRProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_type": "OCRProcessingError", "message": exc.message},
        )

    # Step 3: Analyze extracted text using single structured Gemini request
    analysis_findings: List[GrammarFinding] = []
    corrected_text = ""
    summary = AnalysisSummary(
        total_findings=0,
        findings_by_category={},
        findings_by_severity={},
        assessment="No readable text detected in the provided image.",
    )

    if extracted_text.strip():
        try:
            analysis_resp = await text_processor_service.grammar_analyzer.analyze(
                text=extracted_text,
                language=language,
                content_type=content_type,
                target_audience=target_audience,
                instructions=instructions,
                brand_context=brand_context,
            )
            analysis_findings = analysis_resp.findings
            corrected_text = analysis_resp.corrected_text
            summary = analysis_resp.summary
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

    # Step 4: Upload to S3-compatible storage if enabled & configured
    stored_image: Optional[StoredImageMetadata] = None
    if save_storage and storage_service.is_configured():
        try:
            stored_image = storage_service.upload_image(
                image_bytes=image_bytes,
                content_type=file.content_type,
                original_filename=file.filename,
                generate_presigned=True,
            )
        except StorageUploadError as exc:
            logger.error("S3 upload failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error_type": "StorageUploadError", "message": exc.message},
            )

    # Step 5 & 6: Persist analysis_history and image_metadata in Supabase
    analysis_id: Optional[str] = None
    created_at_str: Optional[str] = None
    image_meta_response: Optional[ImageMetadataResponse] = None

    if save_history and supabase_service.is_configured():
        try:
            findings_data = [f.model_dump() for f in analysis_findings]
            history_record = supabase_service.save_analysis_history(
                input_type="image",
                original_text=extracted_text,
                corrected_text=corrected_text,
                findings=findings_data,
                summary=summary.assessment,
                model_name=settings.effective_model,
                user_id=user_id,
            )
            analysis_id = history_record["id"]
            created_at_str = history_record.get("created_at")

            if stored_image:
                try:
                    meta_record = supabase_service.save_image_metadata(
                        analysis_id=analysis_id,
                        bucket_name=stored_image.bucket_name,
                        object_key=stored_image.object_key,
                        content_type=stored_image.content_type,
                        file_size_bytes=stored_image.file_size_bytes,
                        original_filename=stored_image.original_filename,
                        storage_provider=stored_image.storage_provider,
                        user_id=user_id,
                    )
                    image_meta_response = ImageMetadataResponse(
                        id=meta_record.get("id"),
                        analysis_id=analysis_id,
                        storage_provider=stored_image.storage_provider,
                        bucket_name=stored_image.bucket_name,
                        object_key=stored_image.object_key,
                        original_filename=stored_image.original_filename,
                        content_type=stored_image.content_type,
                        file_size_bytes=stored_image.file_size_bytes,
                        presigned_url=stored_image.presigned_url,
                        created_at=meta_record.get("created_at"),
                    )
                except Exception as meta_exc:
                    # Compensation: remove S3 object if metadata insertion fails
                    logger.error("Image metadata persistence failed; cleaning up S3 object %s: %s", stored_image.object_key, meta_exc)
                    try:
                        storage_service.delete_image(stored_image.object_key)
                    except Exception as del_err:
                        logger.error("Failed to compensate/delete S3 object %s: %s", stored_image.object_key, del_err)
                    raise DatabaseError(f"Failed to save image metadata: {str(meta_exc)}")

        except Exception as db_exc:
            logger.error("Database operation failed during image analysis: %s", db_exc)
            # If S3 upload succeeded but DB failed entirely, clean up uploaded S3 object
            if stored_image and not image_meta_response:
                try:
                    storage_service.delete_image(stored_image.object_key)
                except Exception as cleanup_err:
                    logger.error("Failed to delete S3 object during rollback: %s", cleanup_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error_type": "DatabaseError", "message": f"Database persistence failed: {str(db_exc)}"},
            )

    elif stored_image:
        image_meta_response = ImageMetadataResponse(
            storage_provider=stored_image.storage_provider,
            bucket_name=stored_image.bucket_name,
            object_key=stored_image.object_key,
            original_filename=stored_image.original_filename,
            content_type=stored_image.content_type,
            file_size_bytes=stored_image.file_size_bytes,
            presigned_url=stored_image.presigned_url,
            created_at=stored_image.created_at,
        )

    return ImageAnalysisResponse(
        id=analysis_id,
        extracted_text=extracted_text,
        ocr_metadata=ocr_metadata,
        findings=analysis_findings,
        corrected_text=corrected_text,
        summary=summary,
        image_metadata=image_meta_response,
        created_at=created_at_str,
    )


# ------------------------------------------------------------------------------
# History Endpoints
# ------------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=HistoryListResponse,
    summary="List analysis history ordered chronologically",
)
async def list_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
) -> HistoryListResponse:
    """Retrieves analysis history from Supabase analysis_history."""
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase database is not configured."},
        )

    user = await get_current_user_optional(authorization)
    user_id = user["user_id"] if user else None

    try:
        records = supabase_service.list_analysis_history(user_id=user_id, limit=limit, offset=offset)
        items: List[AnalysisHistoryItem] = []

        for row in records:
            analysis_id = row["id"]
            img_meta = None
            if row.get("input_type") == "image":
                meta_row = supabase_service.get_image_metadata_by_analysis(analysis_id)
                if meta_row:
                    presigned = None
                    if storage_service.is_configured() and meta_row.get("object_key"):
                        try:
                            presigned = storage_service.generate_presigned_url(meta_row["object_key"])
                        except Exception:
                            pass

                    img_meta = ImageMetadataResponse(
                        id=meta_row.get("id"),
                        analysis_id=analysis_id,
                        storage_provider=meta_row.get("storage_provider", "s3"),
                        bucket_name=meta_row.get("bucket_name", ""),
                        object_key=meta_row.get("object_key", ""),
                        original_filename=meta_row.get("original_filename"),
                        content_type=meta_row.get("content_type", ""),
                        file_size_bytes=meta_row.get("file_size_bytes"),
                        presigned_url=presigned,
                        created_at=meta_row.get("created_at"),
                    )

            items.append(
                AnalysisHistoryItem(
                    id=analysis_id,
                    user_id=row.get("user_id"),
                    input_type=row.get("input_type", "text"),
                    original_text=row.get("original_text", ""),
                    corrected_text=row.get("corrected_text", ""),
                    findings=row.get("findings") or [],
                    summary=row.get("summary"),
                    model_name=row.get("model_name"),
                    created_at=row.get("created_at", ""),
                    image_metadata=img_meta,
                )
            )

        return HistoryListResponse(
            items=items,
            total=len(items),
            limit=limit,
            offset=offset,
        )

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "DatabaseError", "message": exc.message},
        )


@router.get(
    "/history/{id}",
    response_model=AnalysisHistoryItem,
    summary="Get single analysis history record by ID",
)
async def get_history_item(
    id: str,
    authorization: Optional[str] = Header(None),
) -> AnalysisHistoryItem:
    """Retrieves a single analysis entry with any associated image metadata."""
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase database is not configured."},
        )

    user = await get_current_user_optional(authorization)
    user_id = user["user_id"] if user else None

    row = supabase_service.get_analysis_by_id(analysis_id=id, user_id=user_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "NotFoundError", "message": f"Analysis with ID '{id}' was not found."},
        )

    img_meta = None
    if row.get("input_type") == "image":
        meta_row = supabase_service.get_image_metadata_by_analysis(id)
        if meta_row:
            presigned = None
            if storage_service.is_configured() and meta_row.get("object_key"):
                try:
                    presigned = storage_service.generate_presigned_url(meta_row["object_key"])
                except Exception:
                    pass

            img_meta = ImageMetadataResponse(
                id=meta_row.get("id"),
                analysis_id=id,
                storage_provider=meta_row.get("storage_provider", "s3"),
                bucket_name=meta_row.get("bucket_name", ""),
                object_key=meta_row.get("object_key", ""),
                original_filename=meta_row.get("original_filename"),
                content_type=meta_row.get("content_type", ""),
                file_size_bytes=meta_row.get("file_size_bytes"),
                presigned_url=presigned,
                created_at=meta_row.get("created_at"),
            )

    return AnalysisHistoryItem(
        id=row["id"],
        user_id=row.get("user_id"),
        input_type=row.get("input_type", "text"),
        original_text=row.get("original_text", ""),
        corrected_text=row.get("corrected_text", ""),
        findings=row.get("findings") or [],
        summary=row.get("summary"),
        model_name=row.get("model_name"),
        created_at=str(row.get("created_at", "")),
        image_metadata=img_meta,
    )


@router.patch(
    "/history/{id}",
    response_model=AnalysisHistoryItem,
    summary="Update an analysis history record (e.g. corrected text, findings, review status)",
)
@router.put(
    "/history/{id}",
    response_model=AnalysisHistoryItem,
    summary="Update an analysis history record",
)
async def update_history_item(
    id: str,
    request: UpdateHistoryRequest,
    authorization: Optional[str] = Header(None),
) -> AnalysisHistoryItem:
    """Updates an existing analysis entry in Supabase analysis_history."""
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase database is not configured."},
        )

    user = await get_current_user_optional(authorization)
    user_id = user["user_id"] if user else None

    try:
        updated = supabase_service.update_analysis_history(
            analysis_id=id,
            corrected_text=request.corrected_text,
            findings=request.findings,
            summary=request.summary,
            user_id=user_id,
        )
        return AnalysisHistoryItem(
            id=updated["id"],
            user_id=updated.get("user_id"),
            input_type=updated.get("input_type", "text"),
            original_text=updated.get("original_text", ""),
            corrected_text=updated.get("corrected_text", ""),
            findings=updated.get("findings") if isinstance(updated.get("findings"), list) else [],
            summary=updated.get("summary"),
            model_name=updated.get("model_name"),
            created_at=str(updated.get("created_at", "")),
        )
    except DatabaseError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(exc).lower()
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=status_code,
            detail={"error_type": "DatabaseError", "message": str(exc)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Update failed: {str(exc)}"},
        )


@router.delete(
    "/history/{id}",
    summary="Delete an analysis history record",
)
async def delete_history_item(
    id: str,
    authorization: Optional[str] = Header(None),
) -> Dict[str, str]:
    """Deletes an analysis history record and triggers cascading deletion of metadata."""
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase database is not configured."},
        )

    user = await get_current_user_optional(authorization)
    user_id = user["user_id"] if user else None

    # Retrieve image metadata first to optionally clean up S3 object
    meta_row = supabase_service.get_image_metadata_by_analysis(id)
    if meta_row and storage_service.is_configured() and meta_row.get("object_key"):
        try:
            storage_service.delete_image(meta_row["object_key"])
        except Exception as exc:
            logger.warning("Could not delete S3 object %s during history deletion: %s", meta_row.get("object_key"), exc)

    deleted = supabase_service.delete_analysis(analysis_id=id, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "NotFoundError", "message": f"Analysis with ID '{id}' was not found or already deleted."},
        )

    return {"message": "Analysis deleted successfully."}


# ------------------------------------------------------------------------------
# PDF Report Generation Endpoints
# ------------------------------------------------------------------------------

@router.post(
    "/generate-report",
    summary="Generate downloadable 2-page PDF audit report",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Downloadable PDF audit report"},
        400: {"model": ErrorResponse, "description": "Invalid report request data"},
        500: {"model": ErrorResponse, "description": "PDF generation failed"},
    },
)
async def generate_report(request: ReportGenerationRequest):
    """Generates a downloadable 2-page BrandProof AI Audit Report in PDF format.
    
    - Page 1: Original text with detected errors marked in red with red underline, executive summary, and findings table.
    - Page 2: Publication-ready corrected text, AI guideline proofs matrix, and reviewer sign-off block.
    """
    try:
        findings_dicts = [f.model_dump() for f in request.findings]
        pdf_bytes = report_generator_service.generate_report_pdf(
            original_text=request.original_text,
            corrected_text=request.corrected_text,
            findings=findings_dicts,
            summary=request.summary,
            title=request.title,
            model_name=request.model_name,
            created_at=request.created_at,
            content_type=request.content_type,
            brand_context=request.brand_context,
        )

        filename = f"BrandProof_Report_{(request.title or 'Analysis').replace(' ', '_')}.pdf"
        # Sanitize filename for HTTP header
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Content-Type": "application/pdf",
            },
        )
    except Exception as exc:
        logger.exception("Failed to generate PDF audit report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "PDFGenerationError", "message": f"Failed to generate report: {str(exc)}"},
        )


@router.get(
    "/report/{id}",
    summary="Download PDF report for a saved analysis from history",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Downloadable PDF audit report"},
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
async def download_analysis_report(id: str, authorization: Optional[str] = Header(None)):
    """Fetches an existing analysis from Supabase and streams its 2-page PDF audit report."""
    if not supabase_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "DatabaseConfigError", "message": "Supabase database is not configured."},
        )

    user = await get_current_user_optional(authorization)
    user_id = user["user_id"] if user else None

    item = supabase_service.get_analysis_by_id(analysis_id=id, user_id=user_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "NotFoundError", "message": f"Analysis with ID '{id}' was not found."},
        )

    findings_raw = item.get("findings") or []
    if isinstance(findings_raw, str):
        try:
            import json
            findings_raw = json.loads(findings_raw)
        except Exception:
            findings_raw = []

    pdf_bytes = report_generator_service.generate_report_pdf(
        original_text=item.get("original_text") or "",
        corrected_text=item.get("corrected_text") or item.get("original_text") or "",
        findings=findings_raw if isinstance(findings_raw, list) else [],
        summary=item.get("summary"),
        title=f"BrandProof AI Audit - {id[:8]}",
        model_name=item.get("model_name"),
        created_at=item.get("created_at"),
    )

    safe_filename = f"BrandProof_Report_{id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Type": "application/pdf",
        },
    )


# ------------------------------------------------------------------------------
# System Health Endpoint
# ------------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Get service health, AI provider, OCR, Supabase, and S3 status",
)
async def health_check() -> HealthResponse:
    """Returns the operational status of all services.
    
    Never exposes API keys, service role keys, or secrets.
    """
    ai_configured = ai_provider_service.is_configured()
    ocr_available = ocr_service.is_available()
    db_configured = supabase_service.is_configured()
    s3_configured = storage_service.is_configured()

    status_str = "healthy" if (ai_configured and ocr_available) else "degraded"

    # Mask Supabase URL if present (e.g. https://xxx.supabase.co -> show host only)
    masked_db_url = None
    if settings.SUPABASE_URL:
        masked_db_url = settings.SUPABASE_URL.split("://")[-1].split("/")[0]

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
        database=DatabaseHealth(
            configured=db_configured,
            url=masked_db_url,
        ),
        storage=StorageHealth(
            configured=s3_configured,
            bucket=settings.S3_BUCKET_NAME if s3_configured else None,
            provider="s3",
        ),
    )
