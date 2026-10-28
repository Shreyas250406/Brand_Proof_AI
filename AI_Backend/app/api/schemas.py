"""Pydantic schemas for BrandProof AI Engine API."""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator


class TextAnalysisRequest(BaseModel):
    """Request schema for direct text grammar analysis."""
    text: str = Field(
        ...,
        min_length=1,
        description="The marketing or text content to analyze.",
        examples=["We is excited to announce our new prodcut launch next Tuesday!"],
    )
    language: Optional[str] = Field(
        default="English",
        description="Primary language of the content.",
        examples=["English"],
    )
    content_type: Optional[str] = Field(
        default=None,
        description="Type of content: advertisement, social media post, email, product description, or general text.",
        examples=["advertisement"],
    )
    target_audience: Optional[str] = Field(
        default=None,
        description="Intended readers or target audience.",
        examples=["general consumers"],
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Optional special guidelines or tone instructions.",
        examples=["Keep the tone professional and exciting."],
    )
    brand_context: Optional[str] = Field(
        default=None,
        description="Optional brand guidelines, preferred terminology, or product names to preserve.",
        examples=["Preserve product name 'BrandFlow360' and avoid changing brand capitalization."],
    )

    @field_validator("text")
    @classmethod
    def validate_text_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Text content cannot be empty or whitespace only.")
        return v


class GrammarFinding(BaseModel):
    """Schema representing an individual grammar or language finding."""
    id: str = Field(..., description="Unique finding identifier.")
    category: str = Field(
        ...,
        description="Category: grammar, spelling, punctuation, clarity, repetition, style, or other.",
    )
    severity: str = Field(
        ...,
        description="Severity level: low, medium, or high.",
    )
    original_text: str = Field(..., description="The problematic or flagged snippet.")
    suggestion: str = Field(..., description="The proposed correction or improvement.")
    explanation: str = Field(..., description="Why the text should be changed.")
    confidence: Optional[float] = Field(
        default=None,
        description="Model-estimated confidence score (0.0 to 1.0).",
    )
    start_offset: Optional[int] = Field(
        default=None,
        description="Zero-based start character offset in original text if determinable.",
    )
    end_offset: Optional[int] = Field(
        default=None,
        description="Zero-based end character offset in original text if determinable.",
    )


class AnalysisSummary(BaseModel):
    """Summary overview of the grammar and language analysis."""
    total_findings: int = Field(..., description="Total number of issues found.")
    findings_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of findings grouped by category.",
    )
    findings_by_severity: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of findings grouped by severity.",
    )
    assessment: str = Field(
        ...,
        description="Concise summary assessment of overall language quality.",
    )


class TextAnalysisResponse(BaseModel):
    """Response schema for text grammar analysis."""
    original_text: str
    findings: List[GrammarFinding]
    corrected_text: str
    summary: AnalysisSummary


class OCRMetadata(BaseModel):
    """Metadata describing OCR extraction results."""
    engine: str
    language: str
    lines_detected: int
    average_confidence: Optional[float] = None
    processing_time_ms: Optional[float] = None


class ExtractTextResponse(BaseModel):
    """Response schema for image OCR extraction without grammar analysis."""
    extracted_text: str
    ocr_metadata: OCRMetadata
    success: bool


class ImageAnalysisResponse(BaseModel):
    """Response schema for image OCR extraction plus grammar analysis."""
    extracted_text: str
    ocr_metadata: OCRMetadata
    findings: List[GrammarFinding]
    corrected_text: str
    summary: AnalysisSummary


class AIProviderHealth(BaseModel):
    """Health information for configured AI model provider."""
    configured: bool
    provider: str
    model: str


class OCRServiceHealth(BaseModel):
    """Health information for OCR extraction service."""
    available: bool
    engine: str
    gpu_enabled: bool


class HealthResponse(BaseModel):
    """System health response schema."""
    status: str
    app_name: str
    version: str
    ai_provider: AIProviderHealth
    ocr_service: OCRServiceHealth


class ErrorResponse(BaseModel):
    """Standardized API error response schema."""
    error_type: str
    message: str
    details: Optional[Dict[str, str]] = None
