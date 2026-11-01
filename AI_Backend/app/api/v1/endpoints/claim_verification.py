"""API endpoints for Evidence-Based Claim Verification."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Header, HTTPException, Query, status

from app.schemas.claim_verification import (
    VerifyClaimRequest,
    VerifyClaimResponse,
    ClaimVerificationHistoryItem,
    ClaimVerificationListResponse,
)
from app.services.claim_verification.evidence_evaluator import claim_evidence_evaluator
from app.services.supabase_service import supabase_service
from app.core.exceptions import (
    AuthenticationError,
    AIProviderError,
    AIProviderResponseError,
    DatabaseError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Claim Verification"])


async def extract_optional_user(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    """Extracts authenticated user if Bearer token is provided and valid."""
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
    except Exception as exc:
        logger.warning("Session verification failed for optional user: %s", exc)
        return None


async def extract_required_user(authorization: Optional[str]) -> Dict[str, Any]:
    """Strictly requires authenticated user via Bearer token."""
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_type": "AuthenticationError", "message": "Missing Authorization header."},
        )
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_type": "AuthenticationError", "message": "Invalid Authorization header format."},
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
            detail={"error_type": "InternalServerError", "message": str(exc)},
        )


@router.post(
    "/verify-claim",
    response_model=VerifyClaimResponse,
    summary="Verify a factual or marketing claim against evidence using Gemini AI",
    status_code=status.HTTP_200_OK,
)
async def verify_claim_endpoint(
    request: VerifyClaimRequest,
    authorization: Optional[str] = Header(None),
):
    """Evaluates the supplied claim strictly against the provided evidence items.

    - Does not browse the web or invent supporting facts.
    - Uses Gemini AI with structured JSON output.
    - If user is authenticated, saves record to Supabase with RLS user isolation.
    - If database fails, returns verification result with saved=False without failing request.
    """
    # 1. Run Gemini evidence evaluation
    try:
        result = await claim_evidence_evaluator.evaluate_claim(
            claim=request.claim,
            evidence=request.evidence,
        )
    except AIProviderError as exc:
        logger.error("AI provider error during claim verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_type": type(exc).__name__, "message": exc.message, "details": exc.details},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "ValidationError", "message": str(exc)},
        )
    except Exception as exc:
        logger.exception("Unhandled error evaluating claim")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "InternalServerError", "message": f"Claim verification failed: {str(exc)}"},
        )

    # 2. Check if user is authenticated and attempt persistence
    user = await extract_optional_user(authorization)
    saved = False
    record_id: Optional[str] = None
    created_at: Optional[str] = None

    if user and user.get("id") and supabase_service.is_configured():
        try:
            evidence_dicts = [e.model_dump() for e in request.evidence]
            record = supabase_service.save_claim_verification(
                claim=request.claim,
                evidence=evidence_dicts,
                verification_status=result.verification_status.value,
                confidence=result.confidence,
                result=result.model_dump(),
                user_id=user["id"],
            )
            saved = True
            record_id = str(record.get("id"))
            created_at = record.get("created_at")
        except Exception as exc:
            # Handle database failures without falsely claiming the verification was saved
            logger.warning("Could not persist claim verification to Supabase: %s", exc)
            saved = False

    return VerifyClaimResponse(
        success=True,
        id=record_id,
        result=result,
        saved=saved,
        created_at=created_at,
    )


@router.get(
    "/claim-verifications",
    response_model=ClaimVerificationListResponse,
    summary="List claim verification history for current authenticated user",
)
async def list_claim_verifications_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    """Returns previous claim verifications associated with the authenticated user."""
    user = await extract_required_user(authorization)

    limit_val = limit.default if hasattr(limit, "default") else int(limit)
    offset_val = offset.default if hasattr(offset, "default") else int(offset)

    try:
        records = supabase_service.list_claim_verifications(
            user_id=user["id"],
            limit=limit_val,
            offset=offset_val,
        )
        items = []
        for r in records:
            items.append(
                ClaimVerificationHistoryItem(
                    id=str(r["id"]),
                    user_id=str(r.get("user_id")) if r.get("user_id") else None,
                    claim=r["claim"],
                    evidence=r.get("evidence") or [],
                    verification_status=r["verification_status"],
                    confidence=float(r["confidence"]) if r.get("confidence") is not None else None,
                    result=r.get("result") or {},
                    created_at=str(r.get("created_at")),
                )
            )
        return ClaimVerificationListResponse(
            success=True,
            verifications=items,
            total=len(items),
        )
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "DatabaseError", "message": exc.message},
        )


@router.get(
    "/claim-verifications/{verification_id}",
    response_model=ClaimVerificationHistoryItem,
    summary="Get single claim verification by ID",
)
async def get_claim_verification_endpoint(
    verification_id: str,
    authorization: Optional[str] = Header(None),
):
    """Retrieves a single claim verification record owned by the authenticated user."""
    user = await extract_required_user(authorization)

    try:
        record = supabase_service.get_claim_verification(
            verification_id=verification_id,
            user_id=user["id"],
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "NotFoundError", "message": "Claim verification not found."},
            )
        return ClaimVerificationHistoryItem(
            id=str(record["id"]),
            user_id=str(record.get("user_id")) if record.get("user_id") else None,
            claim=record["claim"],
            evidence=record.get("evidence") or [],
            verification_status=record["verification_status"],
            confidence=float(record["confidence"]) if record.get("confidence") is not None else None,
            result=record.get("result") or {},
            created_at=str(record.get("created_at")),
        )
    except HTTPException:
        raise
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "DatabaseError", "message": exc.message},
        )


@router.delete(
    "/claim-verifications/{verification_id}",
    summary="Delete a claim verification record",
)
async def delete_claim_verification_endpoint(
    verification_id: str,
    authorization: Optional[str] = Header(None),
):
    """Deletes a verification record owned by the authenticated user."""
    user = await extract_required_user(authorization)

    try:
        deleted = supabase_service.delete_claim_verification(
            verification_id=verification_id,
            user_id=user["id"],
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "NotFoundError", "message": "Claim verification not found or already deleted."},
            )
        return {"success": True, "message": "Claim verification deleted successfully."}
    except HTTPException:
        raise
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "DatabaseError", "message": exc.message},
        )
