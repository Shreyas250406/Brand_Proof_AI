"""Pydantic schemas for Evidence-Based Claim Verification."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class VerificationStatus(str, Enum):
    """The 5 canonical semantic verification statuses for claim verification."""
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNVERIFIABLE = "UNVERIFIABLE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class EvidenceRelationship(str, Enum):
    """Relationship between an individual piece of evidence and the claim."""
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    PARTIALLY_SUPPORTS = "PARTIALLY_SUPPORTS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NEUTRAL_CONTEXT = "NEUTRAL_CONTEXT"


class EvidenceRelevance(str, Enum):
    """Relevance level of the evidence to the claim."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    IRRELEVANT = "IRRELEVANT"


class EvidenceItem(BaseModel):
    """A user-supplied piece of evidence/proof."""
    id: str = Field(default="E001", description="Unique identifier for this evidence item within the request")
    title: str = Field(..., min_length=1, max_length=300, description="Title or descriptor of the evidence")
    text: str = Field(..., min_length=1, max_length=10000, description="Evidence text passage or extracted quote")
    source_url: Optional[str] = Field(None, max_length=1000, description="Optional web link to source material")
    publisher: Optional[str] = Field(None, max_length=200, description="Optional publisher or organization")
    published_date: Optional[str] = Field(None, max_length=50, description="Optional publication date or year")
    evidence_type: Optional[str] = Field(
        "unknown",
        description="Optional user-provided label ('supporting', 'contradicting', 'neutral', 'unknown')",
    )

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip()
        if not v_clean:
            return None
        if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
            raise ValueError("source_url must start with http:// or https://")
        return v_clean


class VerifyClaimRequest(BaseModel):
    """Input payload to verify a factual or marketing claim against evidence."""
    claim: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The marketing or factual claim to be verified",
    )
    evidence: List[EvidenceItem] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of 1 to 10 evidence items to evaluate against the claim",
    )

    @field_validator("claim")
    @classmethod
    def validate_claim_not_blank(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Claim must contain at least 3 non-whitespace characters.")
        return cleaned


class EvidenceAnalysisItem(BaseModel):
    """Detailed evaluation of how a single piece of evidence relates to the claim."""
    evidence_id: str
    relationship: str = Field(
        ...,
        description="Evaluated relationship (e.g. SUPPORTS, CONTRADICTS, PARTIALLY_SUPPORTS, INSUFFICIENT_EVIDENCE, NEUTRAL_CONTEXT)",
    )
    relevance: str = Field(
        "MEDIUM",
        description="Relevance level (HIGH, MEDIUM, LOW, IRRELEVANT)",
    )
    matched_passage: Optional[str] = Field(
        None,
        description="Exact quote or key passage from the evidence that influenced the verdict",
    )
    explanation: str = Field(
        ...,
        description="Clear rationale explaining the relationship to the claim",
    )


class ClaimVerificationResult(BaseModel):
    """Structured evaluation result produced by Gemini for the claim verification."""
    verification_status: VerificationStatus
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI estimated confidence score (0.0 to 1.0)",
    )
    claim_summary: str = Field(
        ...,
        description="Concise neutral summary of the claim being evaluated",
    )
    verdict: str = Field(
        ...,
        description="Executive verdict summarizing whether the evidence proves or disproves the claim",
    )
    reasoning: str = Field(
        ...,
        description="Comprehensive explanation detailing how the evidence establishes or fails to establish the claim",
    )
    evidence_analysis: List[EvidenceAnalysisItem] = Field(
        default_factory=list,
        description="Evidence-by-evidence detailed evaluation",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Gaps, missing facts, or unproven aspects needed for full verification",
    )
    suggested_correction: Optional[str] = Field(
        None,
        description="Optional truthful claim phrasing accurately backed by the provided evidence",
    )

    @field_validator("verification_status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> VerificationStatus:
        if isinstance(v, VerificationStatus):
            return v
        if isinstance(v, str):
            clean = v.strip().upper().replace(" ", "_")
            # Map common variations safely
            if clean in ("SUPPORTED", "VERIFIED", "PROVEN"):
                return VerificationStatus.SUPPORTED
            if clean in ("CONTRADICTED", "DISPROVEN", "FALSE", "REFUTED"):
                return VerificationStatus.CONTRADICTED
            if clean in ("PARTIALLY_SUPPORTED", "PARTIAL", "PARTIALLY_TRUE"):
                return VerificationStatus.PARTIALLY_SUPPORTED
            if clean in ("UNVERIFIABLE", "UNVERIFIED", "INSUFFICIENT_EVIDENCE", "INSUFFICIENT"):
                return VerificationStatus.UNVERIFIABLE
            if clean in ("CONFLICTING_EVIDENCE", "CONFLICTING", "DISPUTED"):
                return VerificationStatus.CONFLICTING_EVIDENCE
            for status in VerificationStatus:
                if status.value == clean:
                    return status
        return VerificationStatus.UNVERIFIABLE


class VerifyClaimResponse(BaseModel):
    """API response returned to frontend client."""
    success: bool = True
    id: Optional[str] = None
    result: ClaimVerificationResult
    saved: bool = False
    created_at: Optional[str] = None


class ClaimVerificationHistoryItem(BaseModel):
    """Saved record representation for claim verification history."""
    id: str
    user_id: Optional[str] = None
    claim: str
    evidence: List[Dict[str, Any]]
    verification_status: str
    confidence: Optional[float] = None
    result: Dict[str, Any]
    created_at: str


class ClaimVerificationListResponse(BaseModel):
    """List response for historical claim verifications."""
    success: bool = True
    verifications: List[ClaimVerificationHistoryItem]
    total: int
