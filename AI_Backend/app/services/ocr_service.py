"""OCR service using PaddleOCR with environment hardening and robust extraction."""

import io
import os
import time
import logging
from importlib.util import find_spec
from typing import Optional, Tuple, List
from PIL import Image

# Ensure oneDNN / mkldnn compatibility flags are set before paddle imports
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from app.core.config import settings
from app.core.exceptions import (
    OCRProcessingError,
    InvalidImageError,
    PayloadTooLargeError,
    UnsupportedMediaError,
)
from app.api.schemas import OCRMetadata

logger = logging.getLogger(__name__)


class OCRService:
    """Manages image validation and real text extraction via PaddleOCR."""

    def __init__(
        self,
        lang: Optional[str] = None,
        use_gpu: Optional[bool] = None,
    ):
        self.lang = lang or settings.OCR_LANG
        self.use_gpu = use_gpu if use_gpu is not None else settings.OCR_USE_GPU
        self._ocr_engine = None

    def _get_engine(self):
        """Lazy loads the PaddleOCR engine to keep startup fast and isolated."""
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR

                device_str = "gpu" if self.use_gpu else "cpu"
                logger.info("Initializing PaddleOCR (lang=%s, device=%s)...", self.lang, device_str)
                try:
                    self._ocr_engine = PaddleOCR(
                        lang=self.lang,
                        device=device_str,
                        enable_mkldnn=False,
                    )
                except (ValueError, TypeError):
                    # Fallback for older PaddleOCR v2 signatures
                    self._ocr_engine = PaddleOCR(
                        lang=self.lang,
                        use_gpu=self.use_gpu,
                        enable_mkldnn=False,
                    )
            except Exception as exc:
                logger.exception("Failed to initialize PaddleOCR engine")
                raise OCRProcessingError(
                    f"Failed to initialize OCR engine: {str(exc)}",
                    details={"engine": settings.OCR_ENGINE},
                )
        return self._ocr_engine

    def is_available(self) -> bool:
        """Determines whether the OCR engine is available."""
        return find_spec("paddleocr") is not None

    def validate_image_bytes(
        self,
        image_bytes: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> None:
        """Validates image payload size, media type, and integrity."""
        # 1. Size check
        if len(image_bytes) == 0:
            raise InvalidImageError("Uploaded image file is empty.")

        if len(image_bytes) > settings.max_upload_size_bytes:
            raise PayloadTooLargeError(
                f"Image size ({len(image_bytes) / (1024 * 1024):.2f}MB) exceeds the maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # 2. Content-type check if provided
        if content_type and content_type.lower() not in [t.lower() for t in settings.ALLOWED_IMAGE_TYPES]:
            # Also check extension if content_type is ambiguous (e.g. application/octet-stream)
            allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
            ext = os.path.splitext(filename or "")[1].lower()
            if ext not in allowed_exts:
                raise UnsupportedMediaError(
                    f"Unsupported image type '{content_type}'. Allowed types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}."
                )

        # 3. Integrity check with Pillow
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()
        except Exception as exc:
            raise InvalidImageError(f"Uploaded file is corrupted or not a readable image: {str(exc)}")

    def extract_text_from_bytes(
        self,
        image_bytes: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Tuple[str, OCRMetadata]:
        """Extracts text and extraction metadata from raw image bytes.

        Guarantees cleanup of any temporary disk assets.
        """
        self.validate_image_bytes(image_bytes, content_type=content_type, filename=filename)

        engine = self._get_engine()
        start_time = time.time()

        # Reopen with PIL to convert into RGB image format for processing
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                rgb_img = img.convert("RGB")
                # Save to a temporary in-memory buffer or temp file if needed
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    rgb_img.save(tmp_path, format="PNG")

        except Exception as exc:
            raise InvalidImageError(f"Failed to prepare image for OCR: {str(exc)}")

        try:
            # Run prediction
            extracted_lines: List[str] = []
            confidences: List[float] = []

            # PaddleOCR predict/ocr
            if hasattr(engine, "predict"):
                results = list(engine.predict(tmp_path))
            else:
                results = engine.ocr(tmp_path)

            # Parse results (compatible with both PaddleOCR v3 pipeline output and v2 format)
            if results and isinstance(results, list):
                for res in results:
                    if isinstance(res, dict):
                        # PaddleOCR v3 dict format
                        texts = res.get("rec_texts", [])
                        scores = res.get("rec_scores", [])
                        for t, s in zip(texts, scores):
                            cleaned_t = str(t).strip()
                            if cleaned_t:
                                extracted_lines.append(cleaned_t)
                                try:
                                    confidences.append(float(s))
                                except (ValueError, TypeError):
                                    pass
                    elif isinstance(res, list):
                        # Classic PaddleOCR v2 format: list of [box, (text, score)]
                        for line in res:
                            if isinstance(line, (list, tuple)) and len(line) >= 2:
                                text_score = line[1]
                                if isinstance(text_score, (list, tuple)) and len(text_score) >= 2:
                                    cleaned_t = str(text_score[0]).strip()
                                    if cleaned_t:
                                        extracted_lines.append(cleaned_t)
                                        try:
                                            confidences.append(float(text_score[1]))
                                        except (ValueError, TypeError):
                                            pass

            full_text = "\n".join(extracted_lines).strip()
            elapsed_ms = round((time.time() - start_time) * 1000.0, 2)
            avg_conf = (
                round(sum(confidences) / len(confidences), 4)
                if confidences
                else None
            )

            metadata = OCRMetadata(
                engine=settings.OCR_ENGINE,
                language=self.lang,
                lines_detected=len(extracted_lines),
                average_confidence=avg_conf,
                processing_time_ms=elapsed_ms,
            )

            return full_text, metadata

        except Exception as exc:
            logger.exception("OCR extraction failed during inference")
            raise OCRProcessingError(f"OCR inference failed: {str(exc)}")
        finally:
            # Guarantee removal of temporary file
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception as cleanup_err:
                    logger.warning("Could not delete temporary OCR file %s: %s", tmp_path, cleanup_err)


ocr_service = OCRService()
