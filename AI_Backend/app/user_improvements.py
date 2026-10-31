"""Standalone User-Driven Content Improvements Module for BrandProof AI.

Accepts existing analyzed content and user-provided instructions,
generates personalized improvement suggestions using Gemini,
and allows users to accept, reject, edit, or regenerate suggestions.
"""

import os
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Supported improvement categories
SUPPORTED_CATEGORIES = [
    "Tone",
    "Clarity",
    "Conciseness",
    "Grammar",
    "Vocabulary",
    "Readability",
    "Professionalism",
    "Marketing effectiveness",
    "Persuasiveness",
    "Brand compliance",
]

DEFAULT_SYSTEM_PROMPT = """You are an expert AI content editor and brand copy specialist for BrandProof AI.
Your task is to analyze the provided content and generate specific, personalized improvement suggestions strictly following the user's instructions.

Guidelines:
1. Target Categories: Tone, Clarity, Conciseness, Grammar, Vocabulary, Readability, Professionalism, Marketing effectiveness, Persuasiveness, Brand compliance.
2. Preserve Entities: You MUST NOT alter, delete, replace, or misspell any preserved entities provided.
3. Brand Guidelines: Follow all provided brand guidelines strictly.
4. Existing Findings: Take existing findings into account. Do not duplicate or contradict them.
5. Accuracy: Do NOT change the original factual meaning or introduce unsupported claims or hallucinations.
6. Granularity: Provide localized, targeted suggestions (replacing specific sentences or phrases) rather than rewriting the entire document as a single suggestion, unless the text is very short.
7. Original Text Matching: Every suggestion's `original_text` MUST be an EXACT, verbatim substring found in the original content.

Output Format:
You must respond with valid JSON matching this schema:
{
    "status": "success",
    "suggestions": [
        {
            "id": "suggestion_1",
            "original_text": "exact substring from original content",
            "suggested_text": "replacement text",
            "category": "One of the target categories",
            "explanation": "Brief rationale for the change",
            "status": "pending"
        }
    ]
}
"""


def _load_env_fallback() -> None:
    """Lightweight .env loader that does not require python-dotenv."""
    search_dirs = [
        Path.cwd(),
        Path.cwd() / "AI_Backend",
        Path(__file__).resolve().parent.parent,
        Path(__file__).resolve().parent.parent.parent,
    ]
    for directory in search_dirs:
        env_file = directory / ".env"
        if env_file.is_file():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass


def get_gemini_config() -> Dict[str, Any]:
    """Retrieves Gemini configuration, reusing existing application settings when available."""
    try:
        from app.core.config import settings
        return {
            "api_key": settings.effective_api_key,
            "model": settings.effective_model,
            "timeout": settings.AI_TIMEOUT_SECONDS,
            "max_retries": settings.AI_MAX_RETRIES,
        }
    except Exception:
        _load_env_fallback()
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY")
        model = os.environ.get("GEMINI_MODEL") or os.environ.get("AI_MODEL") or "gemini-3.5-flash-lite"
        timeout = float(os.environ.get("AI_TIMEOUT_SECONDS", "30.0"))
        max_retries = int(os.environ.get("AI_MAX_RETRIES", "2"))
        return {
            "api_key": api_key.strip() if api_key else None,
            "model": model.strip(),
            "timeout": timeout,
            "max_retries": max_retries,
        }


def _clean_json_response(raw_text: str) -> str:
    """Strips markdown code fences and extracts raw JSON from model response."""
    text = raw_text.strip()
    # Strip markdown code blocks
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    return text


def build_user_prompt(
    original_content: str,
    user_instructions: str,
    existing_findings: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Constructs the prompt for Gemini with all required context sections."""
    ctx = context or {}
    content_type = ctx.get("content_type", "General")
    target_audience = ctx.get("target_audience", "General Audience")
    language = ctx.get("language", "English")
    brand_guidelines = ctx.get("brand_guidelines", [])
    preserved_entities = ctx.get("preserved_entities", [])
    findings = existing_findings or []

    prompt_parts = [
        "## CONTENT CONTEXT",
        f"- Content Type: {content_type}",
        f"- Target Audience: {target_audience}",
        f"- Language: {language}",
    ]

    if brand_guidelines:
        prompt_parts.append("- Brand Guidelines:")
        for bg in brand_guidelines:
            prompt_parts.append(f"  * {bg}")
    else:
        prompt_parts.append("- Brand Guidelines: None specified")

    if preserved_entities:
        prompt_parts.append("- Preserved Entities (DO NOT ALTER):")
        for entity in preserved_entities:
            prompt_parts.append(f"  * {entity}")
    else:
        prompt_parts.append("- Preserved Entities: None specified")

    if findings:
        prompt_parts.append("\n## EXISTING FINDINGS (From prior analysis):")
        prompt_parts.append(json.dumps(findings, indent=2))
    else:
        prompt_parts.append("\n## EXISTING FINDINGS: None")

    prompt_parts.append("\n## ORIGINAL CONTENT:")
    prompt_parts.append(original_content.strip())

    prompt_parts.append("\n## USER INSTRUCTIONS:")
    prompt_parts.append(user_instructions.strip())

    prompt_parts.append(
        "\nGenerate localized improvement suggestions based strictly on the user instructions "
        "and content context. Return a JSON object with 'status' and 'suggestions'."
    )

    return "\n".join(prompt_parts)


def get_gemini_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sends a prompt to the Gemini API and returns the parsed JSON response.

    Uses existing application configuration and client where available, with
    an independent adapter fallback supporting standard urllib and bounded retries.
    """
    cfg = config or get_gemini_config()
    api_key = cfg.get("api_key")
    if not api_key:
        raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY.")

    model = cfg.get("model", "gemini-3.5-flash-lite")
    timeout = cfg.get("timeout", 30.0)
    max_retries = cfg.get("max_retries", 2)
    sys_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {
            "parts": [{"text": sys_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2,
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            # First attempt httpx if available
            try:
                import httpx
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(
                        url,
                        content=payload_bytes,
                        headers={"Content-Type": "application/json"},
                    )
                    status_code = resp.status_code
                    resp_text = resp.text
            except ImportError:
                # Standalone fallback using standard library urllib
                import urllib.request
                import urllib.error
                req = urllib.request.Request(
                    url,
                    data=payload_bytes,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as response:
                        status_code = response.getcode()
                        resp_text = response.read().decode("utf-8")
                except urllib.error.HTTPError as he:
                    status_code = he.code
                    resp_text = he.read().decode("utf-8")

            if status_code == 200:
                data = json.loads(resp_text)
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini returned no candidates in response (possible safety block).")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise RuntimeError("Gemini returned empty content parts.")
                raw_text = parts[0].get("text", "")
                cleaned_text = _clean_json_response(raw_text)
                return json.loads(cleaned_text)

            if status_code in (429, 503) and attempt < max_retries:
                delay = min((1.5 ** attempt) + 0.5, 5.0)
                time.sleep(delay)
                continue

            raise RuntimeError(f"Gemini API returned HTTP {status_code}: {resp_text[:300]}")

        except Exception as exc:
            last_error = exc
            if attempt < max_retries and ("timeout" in str(exc).lower() or "connection" in str(exc).lower()):
                time.sleep(1.0)
                continue
            break

    raise RuntimeError(f"Failed to communicate with Gemini API: {last_error}")


def generate_improvements(
    original_content: str,
    user_instructions: str,
    existing_findings: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
    gemini_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generates personalized improvement suggestions using Gemini.

    Validates inputs, constructs the prompt, invokes Gemini, validates the
    structured output, and returns suggestions with 'pending' status.
    """
    if not isinstance(original_content, str) or not original_content.strip():
        return {
            "status": "error",
            "message": "Original content cannot be empty.",
            "suggestions": [],
        }

    if not isinstance(user_instructions, str) or not user_instructions.strip():
        return {
            "status": "error",
            "message": "User instructions cannot be empty.",
            "suggestions": [],
        }

    prompt = build_user_prompt(
        original_content=original_content,
        user_instructions=user_instructions,
        existing_findings=existing_findings,
        context=context,
    )

    caller = gemini_client or get_gemini_response

    try:
        raw_response = caller(prompt, DEFAULT_SYSTEM_PROMPT)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Gemini response error: {str(exc)}",
            "suggestions": [],
        }

    # Handle if raw_response is string or non-dict
    if isinstance(raw_response, str):
        try:
            raw_response = json.loads(_clean_json_response(raw_response))
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Malformed JSON from Gemini: {str(exc)}",
                "suggestions": [],
            }

    if isinstance(raw_response, list):
        raw_suggestions = raw_response
    elif isinstance(raw_response, dict):
        raw_suggestions = raw_response.get("suggestions", [])
        if not isinstance(raw_suggestions, list):
            raw_suggestions = []
    else:
        return {
            "status": "error",
            "message": "Invalid response format received from Gemini.",
            "suggestions": [],
        }

    validated_suggestions: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_suggestions):
        if not isinstance(item, dict):
            continue

        orig_text = str(item.get("original_text", "")).strip()
        sugg_text = str(item.get("suggested_text", "")).strip()

        if not orig_text or not sugg_text:
            continue

        sugg_id = str(item.get("id") or f"suggestion_{idx + 1}").strip()
        category = str(item.get("category") or "Clarity").strip()
        explanation = str(item.get("explanation") or "").strip()

        validated_suggestions.append({
            "id": sugg_id,
            "original_text": orig_text,
            "suggested_text": sugg_text,
            "category": category,
            "explanation": explanation,
            "status": "pending",
        })

    return {
        "status": "success",
        "suggestions": validated_suggestions,
    }


def accept_suggestion(
    suggestions: List[Dict[str, Any]],
    suggestion_id: str,
) -> List[Dict[str, Any]]:
    """Marks the specified suggestion as accepted."""
    if not isinstance(suggestions, list):
        return []
    for s in suggestions:
        if isinstance(s, dict) and s.get("id") == suggestion_id:
            s["status"] = "accepted"
            break
    return suggestions


def reject_suggestion(
    suggestions: List[Dict[str, Any]],
    suggestion_id: str,
) -> List[Dict[str, Any]]:
    """Marks the specified suggestion as rejected."""
    if not isinstance(suggestions, list):
        return []
    for s in suggestions:
        if isinstance(s, dict) and s.get("id") == suggestion_id:
            s["status"] = "rejected"
            break
    return suggestions


def edit_suggestion(
    suggestions: List[Dict[str, Any]],
    suggestion_id: str,
    edited_text: str,
) -> List[Dict[str, Any]]:
    """Modifies the suggested text of the specified suggestion."""
    if not isinstance(suggestions, list):
        return []
    for s in suggestions:
        if isinstance(s, dict) and s.get("id") == suggestion_id:
            s["suggested_text"] = edited_text
            s["is_edited"] = True
            break
    return suggestions


def accept_all_suggestions(
    suggestions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Marks all currently pending suggestions as accepted."""
    if not isinstance(suggestions, list):
        return []
    for s in suggestions:
        if isinstance(s, dict) and s.get("status") == "pending":
            s["status"] = "accepted"
    return suggestions


def restore_original(original_content: str) -> str:
    """Restores and returns the original content unmodified."""
    if original_content is None:
        return ""
    return str(original_content)


def apply_accepted_suggestions(
    original_content: str,
    suggestions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Applies only accepted suggestions to the original content safely."""
    raise NotImplementedError("apply_accepted_suggestions not yet implemented.")


def regenerate_improvements(
    original_content: str,
    new_instructions: str,
    previous_suggestions: Optional[List[Dict[str, Any]]] = None,
    existing_findings: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates a fresh batch of suggestions based on new instructions."""
    raise NotImplementedError("regenerate_improvements not yet implemented.")
