"""Claim verification service module."""

from app.services.claim_verification.evidence_evaluator import (
    ClaimEvidenceEvaluator,
    claim_evidence_evaluator,
)

__all__ = ["ClaimEvidenceEvaluator", "claim_evidence_evaluator"]
