"""Shared test fixtures and utilities for BrandProof AI."""

import io
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Returns a FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture
def create_test_image():
    """Factory fixture to create valid image bytes containing text."""
    def _create(text: str = "BrandProof AI Test", size: tuple = (250, 70)) -> bytes:
        img = Image.new("RGB", size, color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((15, 25), text, fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    return _create


@pytest.fixture
def corrupted_image_bytes() -> bytes:
    """Returns corrupted image bytes that fail image integrity checks."""
    return b"NOT_A_VALID_IMAGE_HEADER_BYTES_1234567890"


@pytest.fixture
def mock_llm_grammar_error_response():
    """Returns a realistic structured Gemini response for text with grammar errors."""
    return {
        "findings": [
            {
                "id": "finding_1",
                "category": "grammar",
                "severity": "high",
                "original_text": "We is",
                "suggestion": "We are",
                "explanation": "Subject-verb agreement error: 'We' takes the plural verb 'are'.",
                "confidence": 0.98,
                "start_offset": 0,
                "end_offset": 5
            },
            {
                "id": "finding_2",
                "category": "spelling",
                "severity": "medium",
                "original_text": "prodcut",
                "suggestion": "product",
                "explanation": "Misspelling of the word 'product'.",
                "confidence": 0.99,
                "start_offset": 28,
                "end_offset": 35
            }
        ],
        "corrected_text": "We are excited to announce our new product launch next Tuesday!",
        "summary": {
            "assessment": "Found 2 errors: 1 subject-verb agreement error and 1 spelling mistake."
        }
    }


@pytest.fixture
def mock_llm_clean_text_response():
    """Returns a Gemini response for text that is already completely correct."""
    return {
        "findings": [],
        "corrected_text": "Our award-winning platform accelerates compliance review by 80%.",
        "summary": {
            "assessment": "No grammatical, spelling, or stylistic errors found."
        }
    }


@pytest.fixture
def mock_llm_ambiguous_text_response():
    """Returns a Gemini response explaining an ambiguous sentence without inventing meaning."""
    return {
        "findings": [
            {
                "id": "finding_1",
                "category": "clarity",
                "severity": "medium",
                "original_text": "The manager told the designer he made a mistake.",
                "suggestion": "The manager informed the designer that the designer had made a mistake [or: that the manager had made a mistake].",
                "explanation": "Ambiguous pronoun reference: 'he' can refer either to the manager or the designer.",
                "confidence": 0.88,
                "start_offset": 0,
                "end_offset": 48
            }
        ],
        "corrected_text": "The manager told the designer that the designer made a mistake.",
        "summary": {
            "assessment": "Flagged 1 clarity issue involving an ambiguous pronoun reference."
        }
    }


@pytest.fixture
def mock_llm_brand_preservation_response():
    """Returns a Gemini response respecting brand context (e.g. 'BrandFlow360' and 'v2.5')."""
    return {
        "findings": [
            {
                "id": "finding_1",
                "category": "grammar",
                "severity": "high",
                "original_text": "has launched",
                "suggestion": "have launched",
                "explanation": "Plural subject-verb agreement correction.",
                "confidence": 0.95,
                "start_offset": 20,
                "end_offset": 32
            }
        ],
        "corrected_text": "BrandFlow360 v2.5 have launched with 10 new features.",
        "summary": {
            "assessment": "Preserved proprietary brand name BrandFlow360 and version v2.5."
        }
    }
