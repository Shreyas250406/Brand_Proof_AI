"""Pydantic schemas for BrandProof AI Engine API."""

from typing import Optional, List, Dict, Any
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
    id: Optional[str] = None
    original_text: str
    findings: List[GrammarFinding]
    corrected_text: str
    summary: AnalysisSummary
    created_at: Optional[str] = None


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


class ImageMetadataResponse(BaseModel):
    """Metadata for uploaded images stored in S3-compatible storage."""
    id: Optional[str] = None
    analysis_id: Optional[str] = None
    storage_provider: str = "s3"
    bucket_name: str
    object_key: str
    original_filename: Optional[str] = None
    content_type: str
    file_size_bytes: Optional[int] = None
    presigned_url: Optional[str] = None
    created_at: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    """Response schema for image OCR extraction plus grammar analysis."""
    id: Optional[str] = None
    extracted_text: str
    ocr_metadata: OCRMetadata
    findings: List[GrammarFinding]
    corrected_text: str
    summary: AnalysisSummary
    image_metadata: Optional[ImageMetadataResponse] = None
    created_at: Optional[str] = None


class AnalysisHistoryItem(BaseModel):
    """Schema representing an item in analysis history."""
    id: str
    user_id: Optional[str] = None
    input_type: str
    original_text: str
    corrected_text: str
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[str] = None
    model_name: Optional[str] = None
    created_at: str
    image_metadata: Optional[ImageMetadataResponse] = None


class HistoryListResponse(BaseModel):
    """Response schema for listing analysis history."""
    items: List[AnalysisHistoryItem]
    total: int
    limit: int
    offset: int


class UserRegisterRequest(BaseModel):
    """Request schema for Supabase user registration."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")
    display_name: Optional[str] = Field(default=None, description="Optional public display name")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = (v or "").strip()
        if not v or "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address format.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if not v or len(v.strip()) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v


class UserLoginRequest(BaseModel):
    """Request schema for user login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = (v or "").strip()
        if not v or "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address format.")
        return v


class AuthResponse(BaseModel):
    """Response schema for authentication operations."""
    user_id: Optional[str] = None
    email: str
    display_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    confirmation_required: bool = False
    message: Optional[str] = None


class UserSessionResponse(BaseModel):
    """Response schema for session verification."""
    user_id: str
    email: str
    display_name: Optional[str] = None


class DatabaseHealth(BaseModel):
    """Health information for Supabase database."""
    configured: bool
    url: Optional[str] = None


class StorageHealth(BaseModel):
    """Health information for S3-compatible storage."""
    configured: bool
    bucket: Optional[str] = None
    provider: str = "s3"


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
    database: Optional[DatabaseHealth] = None
    storage: Optional[StorageHealth] = None


class ErrorResponse(BaseModel):
    """Standardized API error response schema."""
    error_type: str
    message: str
    details: Optional[Dict[str, str]] = None


class ReportFindingInput(BaseModel):
    """Input finding item for report generation."""
    id: Optional[str] = None
    category: str = "grammar"
    severity: str = "medium"
    original_text: str
    suggestion: str
    explanation: str
    rule: Optional[str] = None
    confidence: Optional[float] = None


class ReportGenerationRequest(BaseModel):
    """Request schema for generating a 2-page PDF compliance and audit report."""
    title: Optional[str] = "BrandProof AI Content Audit Report"
    original_text: str
    corrected_text: str
    findings: List[ReportFindingInput] = []
    summary: Optional[str] = None
    brand_context: Optional[str] = None
    content_type: Optional[str] = None
    model_name: Optional[str] = "Gemini 3.5 Flash"
    created_at: Optional[str] = None

