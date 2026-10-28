"""Tests for OCR text extraction and image validation service."""

import pytest
from app.services.ocr_service import OCRService
from app.core.exceptions import (
    InvalidImageError,
    UnsupportedMediaError,
    PayloadTooLargeError,
)
from app.core.config import settings


def test_ocr_service_available():
    """Verifies that the OCR service engine is installed and reported as available."""
    service = OCRService()
    assert service.is_available() is True


def test_valid_image_ocr_extraction(create_test_image):
    """Scenario 6: Valid image OCR extraction using real PaddleOCR engine."""
    service = OCRService()
    img_bytes = create_test_image(text="BrandProof AI Quality", size=(350, 80))

    extracted_text, metadata = service.extract_text_from_bytes(
        image_bytes=img_bytes,
        content_type="image/png",
        filename="test.png",
    )

    assert isinstance(extracted_text, str)
    assert len(extracted_text) > 0
    assert "Brand" in extracted_text or "Proof" in extracted_text or "AI" in extracted_text
    assert metadata.engine == settings.OCR_ENGINE
    assert metadata.lines_detected >= 1
    assert metadata.processing_time_ms is not None
    assert metadata.processing_time_ms > 0


def test_unreadable_corrupted_image(corrupted_image_bytes):
    """Scenario 7: Unreadable or corrupted image raises InvalidImageError."""
    service = OCRService()
    with pytest.raises(InvalidImageError) as exc_info:
        service.extract_text_from_bytes(
            image_bytes=corrupted_image_bytes,
            content_type="image/png",
            filename="corrupt.png",
        )
    assert "corrupted" in str(exc_info.value).lower() or "not a readable image" in str(exc_info.value).lower()


def test_empty_image_bytes():
    """Empty image byte array raises InvalidImageError."""
    service = OCRService()
    with pytest.raises(InvalidImageError) as exc_info:
        service.extract_text_from_bytes(
            image_bytes=b"",
            content_type="image/png",
            filename="empty.png",
        )
    assert "empty" in str(exc_info.value).lower()


def test_unsupported_file_format():
    """Scenario 8: Unsupported file format raises UnsupportedMediaError."""
    service = OCRService()
    dummy_pdf = b"%PDF-1.4 dummy pdf content"
    with pytest.raises(UnsupportedMediaError) as exc_info:
        service.extract_text_from_bytes(
            image_bytes=dummy_pdf,
            content_type="application/pdf",
            filename="document.pdf",
        )
    assert "unsupported image type" in str(exc_info.value).lower()


def test_oversized_image_upload(create_test_image, monkeypatch):
    """Scenario 9: Image exceeding maximum allowed size raises PayloadTooLargeError."""
    service = OCRService()
    img_bytes = create_test_image("Small Text")

    # Temporarily set max upload size to a very small threshold
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)

    with pytest.raises(PayloadTooLargeError) as exc_info:
        service.extract_text_from_bytes(
            image_bytes=img_bytes,
            content_type="image/png",
            filename="oversized.png",
        )
    assert "exceeds the maximum allowed limit" in str(exc_info.value).lower()
