"""Text processor coordinating OCR text extraction and grammar analysis pipeline."""

import logging
from typing import Optional, Tuple
from app.api.schemas import (
    TextAnalysisRequest,
    TextAnalysisResponse,
    ImageAnalysisResponse,
    ExtractTextResponse,
    OCRMetadata,
    AnalysisSummary,
)
from app.core.config import settings
from app.core.exceptions import (
    PayloadTooLargeError,
    OCRProcessingError,
)
from app.services.grammar_analyzer import (
    GrammarAnalyzerService,
    grammar_analyzer_service,
)
from app.services.ocr_service import (
    OCRService,
    ocr_service,
)

logger = logging.getLogger(__name__)


class TextProcessorService:
    """Coordinates the text normalization, OCR pipelines, and grammar analysis."""

    def __init__(
        self,
        grammar_analyzer: Optional[GrammarAnalyzerService] = None,
        ocr: Optional[OCRService] = None,
    ):
        self.grammar_analyzer = grammar_analyzer or grammar_analyzer_service
        self.ocr = ocr or ocr_service

    def normalize_text(self, text: str) -> str:
        """Normalizes input text without altering intentional phrasing or formatting."""
        if not text:
            return ""

        if len(text) > settings.MAX_TEXT_LENGTH:
            raise PayloadTooLargeError(
                f"Input text exceeds maximum allowed length of {settings.MAX_TEXT_LENGTH} characters (received {len(text)})."
            )

        # Standardize line endings to \n
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.strip()

    async def process_text_analysis(
        self, request: TextAnalysisRequest
    ) -> TextAnalysisResponse:
        """Coordinates direct text grammar and language analysis."""
        cleaned_text = self.normalize_text(request.text)

        return await self.grammar_analyzer.analyze(
            text=cleaned_text,
            language=request.language,
            content_type=request.content_type,
            target_audience=request.target_audience,
            instructions=request.instructions,
            brand_context=request.brand_context,
        )

    def process_image_extraction(
        self,
        image_bytes: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Tuple[str, OCRMetadata]:
        """Extracts text from image bytes using OCR service."""
        return self.ocr.extract_text_from_bytes(
            image_bytes=image_bytes,
            content_type=content_type,
            filename=filename,
        )

    async def process_image_analysis(
        self,
        image_bytes: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        language: Optional[str] = "English",
        analysis_content_type: Optional[str] = None,
        target_audience: Optional[str] = None,
        instructions: Optional[str] = None,
        brand_context: Optional[str] = None,
    ) -> ImageAnalysisResponse:
        """Extracts text from image and executes grammar analysis pipeline."""
        extracted_text, ocr_metadata = self.process_image_extraction(
            image_bytes=image_bytes,
            content_type=content_type,
            filename=filename,
        )

        # If OCR returned empty text (e.g. image contains no text)
        if not extracted_text.strip():
            return ImageAnalysisResponse(
                extracted_text="",
                ocr_metadata=ocr_metadata,
                findings=[],
                corrected_text="",
                summary=AnalysisSummary(
                    total_findings=0,
                    findings_by_category={},
                    findings_by_severity={},
                    assessment="No readable text detected in the provided image.",
                ),
            )

        analysis_response = await self.grammar_analyzer.analyze(
            text=extracted_text,
            language=language,
            content_type=analysis_content_type,
            target_audience=target_audience,
            instructions=instructions,
            brand_context=brand_context,
        )

        return ImageAnalysisResponse(
            extracted_text=extracted_text,
            ocr_metadata=ocr_metadata,
            findings=analysis_response.findings,
            corrected_text=analysis_response.corrected_text,
            summary=analysis_response.summary,
        )


text_processor_service = TextProcessorService()
