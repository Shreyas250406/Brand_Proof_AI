"""OCR service using PaddleOCR with environment hardening, intelligent preprocessing,

and spatial layout reconstruction for accurate text extraction.
"""

import io
import os
import time
import logging
from importlib.util import find_spec
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image, ImageOps, ImageEnhance

# Ensure oneDNN / mkldnn compatibility flags are set before paddle imports
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
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
    """Manages robust image preprocessing, validation, and layout-aware text

    extraction via PaddleOCR.
    """

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
                    # Fallback for older PaddleOCR signatures
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

    def _preprocess_image(self, image_bytes: bytes) -> Image.Image:
        """Preprocesses image to maximize OCR recognition accuracy:

        - Corrects EXIF camera orientation.
        - Composites transparent/alpha channels on solid white (preventing black-on-black text obliteration).
        - Adds protective border padding (prevents edge text truncation and clipped letters).
        - Smoothly upscales small images to ensure small fonts and fine print are detected.
        - Enhances edge contrast for sharper letter contours.
        """
        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            # 1. Auto-orient based on EXIF tag
            try:
                img = ImageOps.exif_transpose(raw_img)
            except Exception:
                img = raw_img.copy()

            # 2. Handle transparency (RGBA, LA, or paletted with transparency)
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img = img.convert("RGBA")
                canvas = Image.new("RGBA", img.size, (255, 255, 255, 255))
                canvas.paste(img, (0, 0), img)
                rgb_img = canvas.convert("RGB")
            else:
                rgb_img = img.convert("RGB")

            # 3. Add protective border padding around perimeter
            # Avoids edge text touching image bounds, which causes detectors to clip starting/ending letters
            pad = max(24, int(min(rgb_img.width, rgb_img.height) * 0.04))
            rgb_img = ImageOps.expand(rgb_img, border=pad, fill="white")

            # 4. Upscale small images for better character discernment
            if rgb_img.width < 1000 or rgb_img.height < 600:
                scale_w = 1200.0 / max(rgb_img.width, 1)
                scale_h = 800.0 / max(rgb_img.height, 1)
                scale = min(2.5, max(scale_w, scale_h))
                if scale > 1.15:
                    new_w = int(rgb_img.width * scale)
                    new_h = int(rgb_img.height * scale)
                    rgb_img = rgb_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 5. Mild edge sharpness boost for clean letter boundaries
            sharpness_enhancer = ImageEnhance.Sharpness(rgb_img)
            rgb_img = sharpness_enhancer.enhance(1.25)

            return rgb_img

    def _sort_and_group_boxes(
        self,
        raw_items: List[Tuple[List[float], str, float]],
    ) -> Tuple[List[str], List[float]]:
        """Sorts detected text boxes into natural top-to-bottom, left-to-right reading order

        and groups fragments on the same line into coherent sentences.

        raw_items: List of (box_coords [xmin, ymin, xmax, ymax], text, confidence)
        """
        if not raw_items:
            return [], []

        # Filter out noise with very low confidence or stray solitary artifacts
        valid_items = []
        for box, text, score in raw_items:
            clean_text = text.strip()
            if not clean_text:
                continue
            # Ignore low confidence single-char non-alphanumeric noise (e.g. solitary '.' or '|' with score < 0.5)
            if len(clean_text) == 1 and not clean_text.isalnum() and score < 0.50:
                continue
            if score < 0.30:
                continue
            valid_items.append((box, clean_text, score))

        if not valid_items:
            return [], []

        # Calculate bounding box metrics: (ymin, xmin, ymax, xmax, center_y, height)
        enriched = []
        for box, text, score in valid_items:
            xmin, ymin, xmax, ymax = box
            center_y = (ymin + ymax) / 2.0
            height = max(1.0, ymax - ymin)
            enriched.append({
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
                "center_y": center_y,
                "height": height,
                "text": text,
                "score": score,
            })

        # Sort items initially by vertical position
        enriched.sort(key=lambda item: item["ymin"])

        # Group items into distinct horizontal lines
        lines: List[List[Dict[str, Any]]] = []
        for item in enriched:
            assigned = False
            for line in lines:
                # Average vertical center of the line
                avg_line_cy = sum(it["center_y"] for it in line) / len(line)
                avg_line_h = sum(it["height"] for it in line) / len(line)
                threshold = max(avg_line_h, item["height"]) * 0.65

                if abs(item["center_y"] - avg_line_cy) < threshold:
                    line.append(item)
                    assigned = True
                    break

            if not assigned:
                lines.append([item])

        # Sort lines top-to-bottom by average ymin
        lines.sort(key=lambda line: sum(it["ymin"] for it in line) / len(line))

        extracted_lines: List[str] = []
        confidences: List[float] = []

        for line in lines:
            # Sort words within line left-to-right
            line.sort(key=lambda item: item["xmin"])
            line_text = " ".join(item["text"] for item in line).strip()
            if line_text:
                extracted_lines.append(line_text)
                for item in line:
                    confidences.append(item["score"])

        return extracted_lines, confidences

    def extract_text_from_bytes(
        self,
        image_bytes: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Tuple[str, OCRMetadata]:
        """Extracts text and extraction metadata from raw image bytes.

        Applies intelligent preprocessing, angle orientation handling, and
        reading-order layout reconstruction. Guarantees cleanup of temporary disk assets.
        """
        self.validate_image_bytes(image_bytes, content_type=content_type, filename=filename)

        engine = self._get_engine()
        start_time = time.time()

        # Step 1: Preprocess image with orientation, padding, scaling, and alpha compositing
        try:
            processed_img = self._preprocess_image(image_bytes)
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                processed_img.save(tmp_path, format="PNG")

        except Exception as exc:
            raise InvalidImageError(f"Failed to prepare image for OCR: {str(exc)}")

        try:
            # Step 2: Run PaddleOCR inference with optimized settings
            # use_doc_unwarping=False avoids warping flat digital banners and cutting off text
            predict_kwargs = {
                "use_doc_unwarping": False,
                "use_textline_orientation": True,
                "use_doc_orientation_classify": True,
                "text_det_unclip_ratio": 1.6,
                "text_rec_score_thresh": 0.30,
            }

            results = None
            if hasattr(engine, "predict"):
                try:
                    results = list(engine.predict(tmp_path, **predict_kwargs))
                except TypeError:
                    results = list(engine.predict(tmp_path))
            else:
                results = engine.ocr(tmp_path)

            raw_items: List[Tuple[List[float], str, float]] = []

            # Step 3: Parse results and collect boxes with coordinates
            if results and isinstance(results, list):
                for res in results:
                    if isinstance(res, dict):
                        # PaddleOCR v3 / PaddleX pipeline dictionary format
                        texts = res.get("rec_texts", [])
                        scores = res.get("rec_scores", [])
                        boxes = res.get("rec_boxes", [])

                        for idx, (t, s) in enumerate(zip(texts, scores)):
                            text_str = str(t).strip()
                            if not text_str:
                                continue
                            try:
                                score_val = float(s)
                            except (ValueError, TypeError):
                                score_val = 0.5

                            # Extract box coordinates [xmin, ymin, xmax, ymax]
                            if idx < len(boxes):
                                b = boxes[idx]
                                if hasattr(b, "tolist"):
                                    b = b.tolist()
                                if isinstance(b, (list, tuple)) and len(b) >= 4:
                                    box_coords = [float(b[0]), float(b[1]), float(b[2]), float(b[3])]
                                else:
                                    box_coords = [0.0, float(idx * 20), 100.0, float((idx + 1) * 20)]
                            else:
                                box_coords = [0.0, float(idx * 20), 100.0, float((idx + 1) * 20)]

                            raw_items.append((box_coords, text_str, score_val))

                    elif isinstance(res, list):
                        # Classic PaddleOCR v2 format: list of [polygon_box, (text, score)]
                        for idx, line in enumerate(res):
                            if isinstance(line, (list, tuple)) and len(line) >= 2:
                                poly = line[0]
                                text_score = line[1]
                                if isinstance(text_score, (list, tuple)) and len(text_score) >= 2:
                                    text_str = str(text_score[0]).strip()
                                    if not text_str:
                                        continue
                                    try:
                                        score_val = float(text_score[1])
                                    except (ValueError, TypeError):
                                        score_val = 0.5

                                    if isinstance(poly, (list, tuple)) and len(poly) >= 4:
                                        x_coords = [p[0] for p in poly]
                                        y_coords = [p[1] for p in poly]
                                        box_coords = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                                    else:
                                        box_coords = [0.0, float(idx * 20), 100.0, float((idx + 1) * 20)]

                                    raw_items.append((box_coords, text_str, score_val))

            # Step 4: Reconstruct human reading order & spatial line grouping
            extracted_lines, confidences = self._sort_and_group_boxes(raw_items)

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
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception as cleanup_err:
                    logger.warning("Could not delete temporary OCR file %s: %s", tmp_path, cleanup_err)


ocr_service = OCRService()
