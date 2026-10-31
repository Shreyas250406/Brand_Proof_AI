"""User-Driven Content Improvements Module for BrandProof AI.

A standalone, testable backend module that accepts existing analyzed content and
user-provided instructions, generates personalized improvement suggestions using
Gemini, and allows users to accept, reject, edit, or regenerate suggestions before
safely applying accepted changes without conflict, data corruption, or unintended modification.
"""

import copy
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx

from app.core.config import settings
from app.core.exceptions import (
    BrandProofAIException,
    AIProviderConfigError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderResponseError,
    AIRateLimitError,
    AIQuotaExhaustedError,
)

logger = logging.getLogger(__name__)

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM_INSTRUCTION = (
    "You are an expert brand editor, copywriter, and proofreading specialist for BrandProof AI.\n"
    "Your objective is to generate personalized, targeted improvement suggestions for marketing content\n"
    "strictly adhering to the user's explicit instructions and brand context.\n\n"
    "CRITICAL RULES:\n"
    "1. Strict User Focus: Tailor suggestions directly to the user's instructions (e.g., tone, clarity,\n"
    "   conciseness, grammar, vocabulary, readability, professionalism, marketing effectiveness,\n"
    "   persuasiveness, brand compliance).\n"
    "2. Grounded Meaning: Preserve the original core factual meaning. Never invent facts or introduce\n"
    "   unsupported claims.\n"
    "3. Entity Preservation: Strictly preserve any specified brand names, product terms, version numbers,\n"
    "   and metrics verbatim unless instructed otherwise.\n"
    "4. Exact Substrings: The 'original_text' of each suggestion MUST match an exact, verbatim,\n"
    "   case-sensitive substring from the original content so it can be reliably located and replaced.\n"
    "5. Granularity: Break suggestions down into granular phrases or sentences so the user can independently\n"
    "   accept, reject, or edit each suggestion.\n"
    "6. Non-Destructive: Do not propose overlapping replacements for the same text span.\n"
    "7. Output Format: Return strictly valid JSON adhering to the specified schema."
)


def build_prompt(
    original_content: str,
    user_instructions: str,
    existing_findings: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
    previous_suggestions: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Constructs the prompt sent to Gemini incorporating all context dimensions."""
    ctx = context or {}
    content_type = ctx.get("content_type", "Marketing Copy")
    target_audience = ctx.get("target_audience", "Business Professionals")
    language = ctx.get("language", "English")
    brand_guidelines = ctx.get("brand_guidelines", [])
    preserved_entities = ctx.get("preserved_entities", [])

    if isinstance(brand_guidelines, list) and brand_guidelines:
        guidelines_str = "\n".join(f"- {g}" for g in brand_guidelines)
    else:
        guidelines_str = "None specified"

    if isinstance(preserved_entities, list) and preserved_entities:
        entities_str = ", ".join(str(e) for e in preserved_entities)
    else:
        entities_str = "None specified"

    if existing_findings:
        findings_str = json.dumps(existing_findings, indent=2)
    else:
        findings_str = "None provided"

    parts = [
        "--- ANALYSIS CONTEXT ---",
        f"Content Type: {content_type}",
        f"Target Audience: {target_audience}",
        f"Language: {language}",
        f"Brand Guidelines:\n{guidelines_str}",
        f"Preserved Entities (MUST PRESERVE VERBATIM): {entities_str}",
        "",
        "--- EXISTING ANALYSIS FINDINGS (FROM PREVIOUS PROOFREADING/OCR) ---",
        findings_str,
        "",
        "--- USER IMPROVEMENT INSTRUCTIONS ---",
        user_instructions.strip(),
        "",
        "--- ORIGINAL CONTENT (VERBATIM DATA) ---",
        original_content,
        "",
    ]

    if previous_suggestions:
        parts.extend([
            "--- PREVIOUS SUGGESTIONS ---",
            json.dumps(previous_suggestions, indent=2),
            "Note: The user is requesting a new batch of suggestions reflecting updated instructions.",
            "Generate fresh suggestions that build upon or complement previous suggestions without regressing.",
            "",
        ])

    parts.extend([
        "--- JSON SCHEMA TO PRODUCE ---",
        "Produce a valid JSON object matching this exact structure:",
        "{",
        '  "status": "success",',
        '  "suggestions": [',
        "    {",
        '      "id": "suggestion_1",',
        '      "original_text": "Exact substring from original content",',
        '      "suggested_text": "Revised replacement text",',
        '      "category": "Conciseness",',
        '      "explanation": "Why this edit fulfills the user instruction.",',
        '      "status": "pending"',
        "    }",
        "  ]",
        "}",
    ])

    return "\n".join(parts)


def _parse_retry_delay(response: httpx.Response, attempt: int) -> float:
    """Calculates exponential backoff delay for rate-limited requests."""
    retry_header = response.headers.get("Retry-After")
    if retry_header:
        try:
            return min(float(retry_header), 10.0)
        except ValueError:
            pass
    try:
        body = response.json()
        error_details = body.get("error", {}).get("details", [])
        for item in error_details:
            if isinstance(item, dict) and "retryDelay" in item:
                match = re.search(r"(\d+(\.\d+)?)", str(item["retryDelay"]))
                if match:
                    return min(float(match.group(1)), 10.0)
    except Exception:
        pass
    return min((1.5 ** attempt) + 0.5, 8.0)


# ============================================================================
# 1. Gemini Integration
# ============================================================================

def get_gemini_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> Union[str, Dict[str, Any]]:
    """Calls Gemini API using existing configuration and credentials.

    Args:
        prompt: User prompt content.
        system_prompt: Optional system instruction text.
        api_key: Optional API key override. Defaults to settings.effective_api_key.
        model: Optional model override. Defaults to settings.effective_model.
        timeout: Request timeout in seconds.
        max_retries: Maximum automatic retries for transient errors.

    Returns:
        Raw text completion string returned by Gemini.
    """
    key = api_key if api_key is not None else settings.effective_api_key
    if not key or not key.strip():
        raise AIProviderConfigError(
            "Gemini API key is missing. Please set GEMINI_API_KEY in your .env file."
        )

    active_model = model or settings.effective_model
    request_timeout = timeout or settings.AI_TIMEOUT_SECONDS
    retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

    url = f"{GEMINI_API_BASE_URL}/{active_model}:generateContent"
    params = {"key": key.strip()}

    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    }
    if system_prompt:
        payload["system_instruction"] = {
            "parts": [{"text": system_prompt}]
        }

    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=request_timeout) as client:
                response = client.post(url, params=params, json=payload)

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise AIProviderResponseError(
                        "Gemini returned no candidates in response (possible safety block)."
                    )
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise AIProviderResponseError("Gemini returned empty content parts.")
                raw_text = parts[0].get("text", "")
                if not raw_text or not raw_text.strip():
                    raise AIProviderResponseError("Gemini returned empty text completion.")
                return raw_text

            if response.status_code == 429:
                resp_text = response.text.lower()
                if "per day" in resp_text or "daily" in resp_text:
                    raise AIQuotaExhaustedError("Gemini daily API quota reached.")
                if attempt < retries:
                    delay = _parse_retry_delay(response, attempt + 1)
                    import time
                    time.sleep(delay)
                    continue
                raise AIRateLimitError("Gemini rate limit exceeded.")

            if response.status_code in (401, 403):
                raise AIProviderConfigError("Gemini authentication failed: Invalid GEMINI_API_KEY.")

            if response.status_code == 404:
                raise AIProviderConfigError(f"Configured Gemini model '{active_model}' not found.")

            if response.status_code == 503 and attempt < retries:
                import time
                time.sleep(min((2.0 ** attempt), 6.0))
                continue

            raise AIProviderError(
                f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}"
            )

        except httpx.TimeoutException:
            if attempt < retries:
                import time
                time.sleep(1.0)
                continue
            raise AIProviderTimeoutError(
                f"Request to Gemini API timed out after {request_timeout}s."
            )
        except (BrandProofAIException, AIProviderError):
            raise
        except Exception as exc:
            raise AIProviderError(f"Unexpected error communicating with Gemini API: {str(exc)}")

    raise AIProviderError("Gemini request failed after all retries.")


def _clean_markdown_json(text: str) -> str:
    """Strips leading/trailing markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_and_validate_suggestions(
    raw_response: Union[str, Dict[str, Any]],
    original_content: str,
    id_offset: int = 0,
) -> Dict[str, Any]:
    """Parses raw Gemini output, validates structure, and normalizes suggestions."""
    if isinstance(raw_response, dict):
        parsed = raw_response
    elif isinstance(raw_response, str):
        cleaned = _clean_markdown_json(raw_response)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON from Gemini response: %s", raw_response[:200])
            return {
                "status": "error",
                "message": f"Malformed JSON from Gemini response: {str(exc)}",
                "suggestions": [],
            }
    else:
        return {
            "status": "error",
            "message": "Unsupported Gemini response type.",
            "suggestions": [],
        }

    raw_suggestions: List[Any] = []
    if isinstance(parsed, dict):
        if "suggestions" in parsed and isinstance(parsed["suggestions"], list):
            raw_suggestions = parsed["suggestions"]
        elif "improvements" in parsed and isinstance(parsed["improvements"], list):
            raw_suggestions = parsed["improvements"]
        elif "findings" in parsed and isinstance(parsed["findings"], list):
            raw_suggestions = parsed["findings"]
    elif isinstance(parsed, list):
        raw_suggestions = parsed

    validated: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_suggestions):
        if not isinstance(item, dict):
            continue
        orig_text = str(item.get("original_text") or "").strip()
        sugg_text = str(item.get("suggested_text") or "").strip()
        if not orig_text:
            continue

        if id_offset > 0:
            sugg_id = f"suggestion_{id_offset + idx + 1}"
        else:
            sugg_id = str(item.get("id") or f"suggestion_{idx + 1}")
        category = str(item.get("category") or "General").strip()
        explanation = str(item.get("explanation") or "").strip()

        validated.append({
            "id": sugg_id,
            "original_text": orig_text,
            "suggested_text": sugg_text,
            "category": category,
            "explanation": explanation,
            "status": "pending",
        })

    return {
        "status": "success",
        "suggestions": validated,
    }


# ============================================================================
# 2. Suggestion Generation
# ============================================================================

def generate_improvements(
    original_content: str,
    user_instructions: str,
    existing_findings: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates personalized improvement suggestions using the Gemini integration.

    Args:
        original_content: The original analyzed text to improve.
        user_instructions: User-provided instructions for desired improvements.
        existing_findings: Findings from earlier grammar/spelling/OCR analysis.
        context: Context dictionary (content_type, target_audience, language, etc.).

    Returns:
        Structured response dictionary with status and list of suggestions.
    """
    if original_content is None or not str(original_content).strip():
        return {
            "status": "error",
            "message": "Original content cannot be empty.",
            "suggestions": [],
        }

    if user_instructions is None or not str(user_instructions).strip():
        return {
            "status": "error",
            "message": "User instructions cannot be empty.",
            "suggestions": [],
        }

    prompt = build_prompt(
        original_content=original_content,
        user_instructions=user_instructions,
        existing_findings=existing_findings,
        context=context,
    )

    try:
        raw_response = get_gemini_response(prompt=prompt, system_prompt=SYSTEM_INSTRUCTION)
    except BrandProofAIException as exc:
        logger.error("AI provider error during suggestion generation: %s", exc)
        return {
            "status": "error",
            "message": f"AI provider error: {str(exc)}",
            "suggestions": [],
        }
    except Exception as exc:
        logger.error("Unexpected error during suggestion generation: %s", exc)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(exc)}",
            "suggestions": [],
        }

    return _parse_and_validate_suggestions(raw_response, original_content)


# ============================================================================
# 3. Suggestion Management
# ============================================================================

def accept_suggestion(
    suggestions: List[Dict[str, Any]],
    suggestion_id: str,
) -> List[Dict[str, Any]]:
    """Marks the selected suggestion as accepted."""
    found = False
    for s in suggestions:
        if s.get("id") == suggestion_id:
            s["status"] = "accepted"
            found = True
            break
    if not found:
        raise ValueError(f"Suggestion with ID '{suggestion_id}' not found.")
    return suggestions


def reject_suggestion(
    suggestions: List[Dict[str, Any]],
    suggestion_id: str,
) -> List[Dict[str, Any]]:
    """Marks the selected suggestion as rejected."""
    found = False
    for s in suggestions:
        if s.get("id") == suggestion_id:
            s["status"] = "rejected"
            found = True
            break
    if not found:
        raise ValueError(f"Suggestion with ID '{suggestion_id}' not found.")
    return suggestions


def edit_suggestion(
    suggestions: List[Dict[str, Any]],
    suggestion_id: str,
    edited_text: str,
) -> List[Dict[str, Any]]:
    """Allows the user to modify the suggested text for a suggestion."""
    found = False
    for s in suggestions:
        if s.get("id") == suggestion_id:
            s["suggested_text"] = edited_text
            found = True
            break
    if not found:
        raise ValueError(f"Suggestion with ID '{suggestion_id}' not found.")
    return suggestions


def accept_all_suggestions(
    suggestions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Accepts all currently pending suggestions. Rejected ones remain rejected."""
    for s in suggestions:
        if s.get("status") == "pending":
            s["status"] = "accepted"
    return suggestions


def restore_original(original_content: str) -> str:
    """Restores the original content without changing it."""
    return str(original_content)


# ============================================================================
# 4. Final Content Generation
# ============================================================================

def _find_non_overlapping_match(
    content: str,
    target: str,
    occupied_spans: List[Tuple[int, int, str]],
) -> Optional[Tuple[int, int]]:
    """Finds an occurrence of target in content that does not overlap existing spans."""
    start = 0
    target_len = len(target)
    while True:
        pos = content.find(target, start)
        if pos == -1:
            break
        candidate_span = (pos, pos + target_len)
        # Check overlap
        overlaps = False
        for occ_start, occ_end, _ in occupied_spans:
            if max(pos, occ_start) < min(pos + target_len, occ_end):
                overlaps = True
                break
        if not overlaps:
            return candidate_span
        start = pos + 1
    return None


def apply_accepted_suggestions(
    original_content: str,
    suggestions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Applies accepted suggestions safely onto original content without conflict or data corruption.

    Enforces:
    - Only accepted suggestions are applied.
    - Rejected suggestions are never applied.
    - Pending suggestions are never applied.
    - Edited suggestions use their modified text.
    - Never mutates the original content object.
    - Overlapping/conflicting suggestions are safely rejected and reported in conflicts.
    - Suggestions not matching original content are reported in conflicts.
    - Prevents duplicate application of the same suggestion ID.

    Returns:
        Structured dictionary containing original content, final content,
        applied suggestions, rejected suggestions, pending suggestions, and conflicts.
    """
    applied_suggestions: List[Dict[str, Any]] = []
    rejected_suggestions: List[Dict[str, Any]] = []
    pending_suggestions: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    seen_ids = set()
    accepted_candidates: List[Dict[str, Any]] = []

    for item in suggestions:
        s = copy.deepcopy(item)
        s_id = s.get("id")
        status = s.get("status")

        if status == "rejected":
            rejected_suggestions.append(s)
            continue
        elif status == "pending":
            pending_suggestions.append(s)
            continue
        elif status == "accepted":
            if s_id in seen_ids:
                conflicts.append({
                    "suggestion_id": s_id,
                    "original_text": s.get("original_text", ""),
                    "reason": f"Duplicate suggestion ID '{s_id}' in input list.",
                    "suggestion": s,
                })
                continue
            seen_ids.add(s_id)
            accepted_candidates.append(s)
        else:
            # Unknown status treated as pending
            pending_suggestions.append(s)

    # Resolve positions and overlaps for accepted candidates
    scheduled_replacements: List[Tuple[int, int, str, Dict[str, Any]]] = []
    occupied_spans: List[Tuple[int, int, str]] = []

    for candidate in accepted_candidates:
        orig_text = candidate.get("original_text", "")
        cand_id = candidate.get("id", "")
        replacement_text = candidate.get("suggested_text", "")

        if not orig_text or orig_text not in original_content:
            conflicts.append({
                "suggestion_id": cand_id,
                "original_text": orig_text,
                "reason": "Original text not found in content.",
                "suggestion": candidate,
            })
            continue

        match_span = _find_non_overlapping_match(original_content, orig_text, occupied_spans)
        if match_span is None:
            # Either no available occurrence or all occurrences overlap with previously accepted edits
            conflicts.append({
                "suggestion_id": cand_id,
                "original_text": orig_text,
                "reason": "Suggestion overlaps or collides with another accepted suggestion.",
                "suggestion": candidate,
            })
            continue

        start_idx, end_idx = match_span
        occupied_spans.append((start_idx, end_idx, cand_id))
        scheduled_replacements.append((start_idx, end_idx, replacement_text, candidate))

    # Apply non-overlapping replacements from right to left (descending offset)
    # This guarantees earlier indices in original_content remain completely valid
    scheduled_replacements.sort(key=lambda x: x[0], reverse=True)

    working_content = str(original_content)
    for start_idx, end_idx, rep_text, cand in scheduled_replacements:
        working_content = working_content[:start_idx] + rep_text + working_content[end_idx:]

    # Sort applied suggestions in order of original content appearance for predictable ordering
    scheduled_replacements.sort(key=lambda x: x[0])
    applied_suggestions = [cand for _, _, _, cand in scheduled_replacements]

    return {
        "original_content": original_content,
        "final_content": working_content,
        "applied_suggestions": applied_suggestions,
        "rejected_suggestions": rejected_suggestions,
        "pending_suggestions": pending_suggestions,
        "conflicts": conflicts,
    }


# ============================================================================
# 5. Regeneration
# ============================================================================

def regenerate_improvements(
    original_content: str,
    new_instructions: str,
    previous_suggestions: Optional[List[Dict[str, Any]]] = None,
    existing_findings: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates a fresh batch of suggestions based on updated instructions and prior context.

    Preserves previous suggestion records in the caller; does not automatically apply
    new suggestions, does not discard accepted suggestions, and does not train or persist
    any AI model preferences.
    """
    if original_content is None or not str(original_content).strip():
        return {
            "status": "error",
            "message": "Original content cannot be empty.",
            "suggestions": [],
        }

    if new_instructions is None or not str(new_instructions).strip():
        return {
            "status": "error",
            "message": "User instructions cannot be empty.",
            "suggestions": [],
        }

    prompt = build_prompt(
        original_content=original_content,
        user_instructions=new_instructions,
        existing_findings=existing_findings,
        context=context,
        previous_suggestions=previous_suggestions,
    )

    id_offset = len(previous_suggestions) if previous_suggestions else 0

    try:
        raw_response = get_gemini_response(prompt=prompt, system_prompt=SYSTEM_INSTRUCTION)
    except BrandProofAIException as exc:
        logger.error("AI provider error during regeneration: %s", exc)
        return {
            "status": "error",
            "message": f"AI provider error: {str(exc)}",
            "suggestions": [],
        }
    except Exception as exc:
        logger.error("Unexpected error during regeneration: %s", exc)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(exc)}",
            "suggestions": [],
        }

    return _parse_and_validate_suggestions(
        raw_response=raw_response,
        original_content=original_content,
        id_offset=id_offset,
    )
