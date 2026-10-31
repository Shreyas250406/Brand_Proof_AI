"""Independent unit tests for user_improvements module.

Validates all 15 core requirements specified in the User-Driven Content Improvements
Module specification, using strictly mocked Gemini calls to prevent API quota usage.
"""

import copy
import json
import pytest
from unittest.mock import patch, MagicMock

from app.user_improvements import (
    get_gemini_response,
    generate_improvements,
    accept_suggestion,
    reject_suggestion,
    edit_suggestion,
    accept_all_suggestions,
    apply_accepted_suggestions,
    restore_original,
    regenerate_improvements,
    build_prompt,
)
from app.core.config import settings
from app.core.exceptions import (
    AIProviderConfigError,
    AIProviderTimeoutError,
    AIProviderError,
    AIRateLimitError,
)


@pytest.fixture
def sample_original_content() -> str:
    return (
        "Our product helps people to manage their work and make things better. "
        "It is fast and very reliable for everyone."
    )


@pytest.fixture
def sample_mock_gemini_response() -> str:
    return json.dumps({
        "status": "success",
        "suggestions": [
            {
                "id": "suggestion_1",
                "original_text": "manage their work",
                "suggested_text": "streamline workflow operations",
                "category": "Conciseness",
                "explanation": "Professional vocabulary conveys greater enterprise capability.",
                "status": "pending",
            },
            {
                "id": "suggestion_2",
                "original_text": "make things better",
                "suggested_text": "enhance overall productivity",
                "category": "Marketing Effectiveness",
                "explanation": "Concrete value proposition replaces vague phrase.",
                "status": "pending",
            },
        ],
    })


# -----------------------------------------------------------------------------
# 1. Gemini Suggestion Generation
# -----------------------------------------------------------------------------
def test_gemini_suggestion_generation(sample_original_content, sample_mock_gemini_response):
    """Test 1: Valid Gemini response correctly generates structured suggestions."""
    with patch("app.user_improvements.get_gemini_response", return_value=sample_mock_gemini_response) as mock_gemini:
        instructions = "Make this copy more professional and persuasive."
        context = {
            "content_type": "Marketing Copy",
            "target_audience": "Enterprise Executives",
            "language": "English",
            "brand_guidelines": ["Maintain an authoritative tone"],
            "preserved_entities": ["AcmeCorp"],
        }
        res = generate_improvements(
            original_content=sample_original_content,
            user_instructions=instructions,
            existing_findings=[],
            context=context,
        )

        mock_gemini.assert_called_once()
        assert res["status"] == "success"
        assert len(res["suggestions"]) == 2

        s1 = res["suggestions"][0]
        assert s1["id"] == "suggestion_1"
        assert s1["original_text"] == "manage their work"
        assert s1["suggested_text"] == "streamline workflow operations"
        assert s1["category"] == "Conciseness"
        assert s1["status"] == "pending"


# -----------------------------------------------------------------------------
# 2. Empty Instructions
# -----------------------------------------------------------------------------
def test_empty_instructions_handling(sample_original_content):
    """Test 2: Empty or whitespace-only instructions fail gracefully without calling Gemini."""
    with patch("app.user_improvements.get_gemini_response") as mock_gemini:
        # None
        res_none = generate_improvements(sample_original_content, None)
        assert res_none["status"] == "error"
        assert "cannot be empty" in res_none["message"].lower()
        assert res_none["suggestions"] == []

        # Empty string
        res_empty = generate_improvements(sample_original_content, "")
        assert res_empty["status"] == "error"
        assert "cannot be empty" in res_empty["message"].lower()

        # Whitespace
        res_ws = generate_improvements(sample_original_content, "   \n\t  ")
        assert res_ws["status"] == "error"
        assert "cannot be empty" in res_ws["message"].lower()

        # Empty original content
        res_no_content = generate_improvements("", "Make it better")
        assert res_no_content["status"] == "error"
        assert "content cannot be empty" in res_no_content["message"].lower()

        mock_gemini.assert_not_called()


# -----------------------------------------------------------------------------
# 3. Invalid Gemini Response
# -----------------------------------------------------------------------------
def test_invalid_gemini_response(sample_original_content):
    """Test 3: Malformed JSON or unexpected payload from Gemini is handled gracefully."""
    # Malformed JSON text
    with patch("app.user_improvements.get_gemini_response", return_value="INVALID_JSON{not_closed"):
        res = generate_improvements(sample_original_content, "Improve this text")
        assert res["status"] == "error"
        assert "malformed" in res["message"].lower()
        assert res["suggestions"] == []

    # API exception
    with patch("app.user_improvements.get_gemini_response", side_effect=AIProviderError("API connection error")):
        res = generate_improvements(sample_original_content, "Improve this text")
        assert res["status"] == "error"
        assert "api connection error" in res["message"].lower()
        assert res["suggestions"] == []


# -----------------------------------------------------------------------------
# 4. Accepting a Suggestion
# -----------------------------------------------------------------------------
def test_accept_suggestion():
    """Test 4: Accepting a specific suggestion transitions status to 'accepted'."""
    suggestions = [
        {"id": "suggestion_1", "status": "pending", "original_text": "foo", "suggested_text": "bar"},
        {"id": "suggestion_2", "status": "pending", "original_text": "baz", "suggested_text": "qux"},
    ]
    updated = accept_suggestion(suggestions, "suggestion_1")
    assert updated[0]["status"] == "accepted"
    assert updated[1]["status"] == "pending"

    # Non-existent ID raises ValueError
    with pytest.raises(ValueError, match="not found"):
        accept_suggestion(suggestions, "non_existent_id")


# -----------------------------------------------------------------------------
# 5. Rejecting a Suggestion
# -----------------------------------------------------------------------------
def test_reject_suggestion():
    """Test 5: Rejecting a specific suggestion transitions status to 'rejected'."""
    suggestions = [
        {"id": "suggestion_1", "status": "pending", "original_text": "foo", "suggested_text": "bar"},
        {"id": "suggestion_2", "status": "pending", "original_text": "baz", "suggested_text": "qux"},
    ]
    updated = reject_suggestion(suggestions, "suggestion_2")
    assert updated[0]["status"] == "pending"
    assert updated[1]["status"] == "rejected"

    # Non-existent ID raises ValueError
    with pytest.raises(ValueError, match="not found"):
        reject_suggestion(suggestions, "invalid_id")


# -----------------------------------------------------------------------------
# 6. Editing a Suggestion
# -----------------------------------------------------------------------------
def test_edit_suggestion():
    """Test 6: User can modify the suggested text for an individual suggestion."""
    suggestions = [
        {"id": "suggestion_1", "status": "pending", "original_text": "work", "suggested_text": "tasks"},
    ]
    updated = edit_suggestion(suggestions, "suggestion_1", "daily responsibilities")
    assert updated[0]["suggested_text"] == "daily responsibilities"

    # Non-existent ID raises ValueError
    with pytest.raises(ValueError, match="not found"):
        edit_suggestion(suggestions, "missing_id", "new text")


# -----------------------------------------------------------------------------
# 7. Accepting All Suggestions
# -----------------------------------------------------------------------------
def test_accept_all_suggestions():
    """Test 7: Accepting all turns all pending suggestions into accepted, leaving rejected untouched."""
    suggestions = [
        {"id": "s1", "status": "pending", "original_text": "a", "suggested_text": "b"},
        {"id": "s2", "status": "rejected", "original_text": "c", "suggested_text": "d"},
        {"id": "s3", "status": "pending", "original_text": "e", "suggested_text": "f"},
    ]
    updated = accept_all_suggestions(suggestions)
    assert updated[0]["status"] == "accepted"
    assert updated[1]["status"] == "rejected"
    assert updated[2]["status"] == "accepted"


# -----------------------------------------------------------------------------
# 8. Applying Accepted Suggestions
# -----------------------------------------------------------------------------
def test_apply_accepted_suggestions(sample_original_content):
    """Test 8: Only accepted suggestions are safely substituted in the final content."""
    suggestions = [
        {
            "id": "s1",
            "original_text": "manage their work",
            "suggested_text": "streamline workflow operations",
            "status": "accepted",
        },
        {
            "id": "s2",
            "original_text": "make things better",
            "suggested_text": "enhance overall productivity",
            "status": "accepted",
        },
    ]

    result = apply_accepted_suggestions(sample_original_content, suggestions)

    expected_content = (
        "Our product helps people to streamline workflow operations and enhance overall productivity. "
        "It is fast and very reliable for everyone."
    )
    assert result["final_content"] == expected_content
    assert len(result["applied_suggestions"]) == 2
    assert len(result["rejected_suggestions"]) == 0
    assert len(result["pending_suggestions"]) == 0
    assert len(result["conflicts"]) == 0


# -----------------------------------------------------------------------------
# 9. Ensuring Rejected Suggestions Are Not Applied
# -----------------------------------------------------------------------------
def test_ensure_rejected_suggestions_not_applied(sample_original_content):
    """Test 9: Rejected suggestions must NEVER be applied to final content."""
    suggestions = [
        {
            "id": "s1",
            "original_text": "manage their work",
            "suggested_text": "streamline workflow operations",
            "status": "accepted",
        },
        {
            "id": "s2",
            "original_text": "make things better",
            "suggested_text": "REJECTED_TEXT_SHOULD_NEVER_APPEAR",
            "status": "rejected",
        },
    ]

    result = apply_accepted_suggestions(sample_original_content, suggestions)

    assert "REJECTED_TEXT_SHOULD_NEVER_APPEAR" not in result["final_content"]
    assert "make things better" in result["final_content"]  # Remains original
    assert "streamline workflow operations" in result["final_content"]

    assert len(result["applied_suggestions"]) == 1
    assert len(result["rejected_suggestions"]) == 1
    assert result["rejected_suggestions"][0]["id"] == "s2"


# -----------------------------------------------------------------------------
# 10. Ensuring Pending Suggestions Are Not Applied
# -----------------------------------------------------------------------------
def test_ensure_pending_suggestions_not_applied(sample_original_content):
    """Test 10: Pending suggestions must NEVER be applied to final content."""
    suggestions = [
        {
            "id": "s1",
            "original_text": "manage their work",
            "suggested_text": "PENDING_TEXT_SHOULD_NEVER_APPEAR",
            "status": "pending",
        },
    ]

    result = apply_accepted_suggestions(sample_original_content, suggestions)

    assert "PENDING_TEXT_SHOULD_NEVER_APPEAR" not in result["final_content"]
    assert result["final_content"] == sample_original_content
    assert len(result["applied_suggestions"]) == 0
    assert len(result["pending_suggestions"]) == 1
    assert result["pending_suggestions"][0]["id"] == "s1"


# -----------------------------------------------------------------------------
# 11. Restoring Original Content
# -----------------------------------------------------------------------------
def test_restoring_original_content(sample_original_content):
    """Test 11: Restoring original content returns the exact, untouched string."""
    restored = restore_original(sample_original_content)
    assert restored == sample_original_content
    assert restored is not None


# -----------------------------------------------------------------------------
# 12. Handling Overlapping Suggestions
# -----------------------------------------------------------------------------
def test_handle_overlapping_suggestions():
    """Test 12: Overlapping suggestions are not silently overwritten; conflicts are reported."""
    content = "The quick brown fox jumps over the lazy dog."

    suggestions = [
        {
            "id": "s1",
            "original_text": "quick brown fox",
            "suggested_text": "speedy brown fox",
            "status": "accepted",
        },
        {
            "id": "s2",
            "original_text": "brown fox jumps",  # Overlaps with "quick brown fox"
            "suggested_text": "russet canine leaps",
            "status": "accepted",
        },
    ]

    result = apply_accepted_suggestions(content, suggestions)

    # First one applied, second flagged as conflict
    assert len(result["applied_suggestions"]) == 1
    assert result["applied_suggestions"][0]["id"] == "s1"
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["suggestion_id"] == "s2"
    assert "overlap" in result["conflicts"][0]["reason"].lower()

    # The text only has the first modification
    assert result["final_content"] == "The speedy brown fox jumps over the lazy dog."


# -----------------------------------------------------------------------------
# 13. Handling Suggestions That Do Not Match Original Text
# -----------------------------------------------------------------------------
def test_handle_unmatched_suggestions(sample_original_content):
    """Test 13: Suggestion targeting text not found in original content is reported as conflict."""
    suggestions = [
        {
            "id": "s1",
            "original_text": "This phrase does not exist in the source content at all.",
            "suggested_text": "Something completely different",
            "status": "accepted",
        },
    ]

    result = apply_accepted_suggestions(sample_original_content, suggestions)

    assert len(result["applied_suggestions"]) == 0
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["suggestion_id"] == "s1"
    assert "not found" in result["conflicts"][0]["reason"].lower()
    assert result["final_content"] == sample_original_content


# -----------------------------------------------------------------------------
# 14. Regenerating Suggestions
# -----------------------------------------------------------------------------
def test_regenerating_suggestions(sample_original_content):
    """Test 14: Regenerating suggestions builds upon prior context with fresh offset IDs."""
    prior_suggestions = [
        {
            "id": "suggestion_1",
            "original_text": "manage their work",
            "suggested_text": "streamline workflow operations",
            "status": "accepted",
        }
    ]

    mock_gemini_new_batch = json.dumps({
        "status": "success",
        "suggestions": [
            {
                "id": "suggestion_1",  # Model returns suggestion_1, module offsets to suggestion_2
                "original_text": "very reliable",
                "suggested_text": "exceptionally dependable",
                "category": "Vocabulary",
                "explanation": "Elevates language quality.",
                "status": "pending",
            }
        ]
    })

    with patch("app.user_improvements.get_gemini_response", return_value=mock_gemini_new_batch) as mock_gemini:
        res = regenerate_improvements(
            original_content=sample_original_content,
            new_instructions="Now make the vocabulary richer without being overly complex.",
            previous_suggestions=prior_suggestions,
            existing_findings=[],
            context={"language": "English"},
        )

        mock_gemini.assert_called_once()
        assert res["status"] == "success"
        assert len(res["suggestions"]) == 1
        # ID is offset to avoid collision with prior suggestions
        assert res["suggestions"][0]["id"] == "suggestion_2"
        assert res["suggestions"][0]["suggested_text"] == "exceptionally dependable"


# -----------------------------------------------------------------------------
# 15. Ensuring Original Content Remains Unchanged
# -----------------------------------------------------------------------------
def test_ensure_original_content_remains_unchanged(sample_original_content):
    """Test 15: Original content object is never mutated or modified."""
    original_copy = str(sample_original_content)

    suggestions = [
        {
            "id": "s1",
            "original_text": "manage their work",
            "suggested_text": "streamline workflows",
            "status": "accepted",
        }
    ]

    result = apply_accepted_suggestions(sample_original_content, suggestions)

    # Input variable remains identical to its pre-call state
    assert sample_original_content == original_copy
    # Result object returns identical original_content
    assert result["original_content"] == original_copy
    # Final content is modified separately
    assert result["final_content"] != original_copy


# -----------------------------------------------------------------------------
# 16. Edited Suggestion Application
# -----------------------------------------------------------------------------
def test_edited_suggestion_uses_edited_text(sample_original_content):
    """Test 16: An edited suggestion applies the user's custom edited text."""
    suggestions = [
        {
            "id": "s1",
            "original_text": "manage their work",
            "suggested_text": "AI_PROPOSED_TEXT",
            "status": "pending",
        }
    ]

    # User modifies text
    edit_suggestion(suggestions, "s1", "collaborate seamlessly on daily tasks")
    # User accepts
    accept_suggestion(suggestions, "s1")

    result = apply_accepted_suggestions(sample_original_content, suggestions)
    assert "collaborate seamlessly on daily tasks" in result["final_content"]
    assert "AI_PROPOSED_TEXT" not in result["final_content"]


# -----------------------------------------------------------------------------
# 17. Duplicate Suggestion ID Protection
# -----------------------------------------------------------------------------
def test_duplicate_suggestion_id_protection(sample_original_content):
    """Test 17: Passing duplicate suggestion IDs reports conflict and avoids double application."""
    suggestions = [
        {
            "id": "s1",
            "original_text": "manage their work",
            "suggested_text": "streamline workflows",
            "status": "accepted",
        },
        {
            "id": "s1",  # Duplicate ID
            "original_text": "manage their work",
            "suggested_text": "streamline workflows",
            "status": "accepted",
        },
    ]

    result = apply_accepted_suggestions(sample_original_content, suggestions)
    assert len(result["applied_suggestions"]) == 1
    assert len(result["conflicts"]) == 1
    assert "duplicate" in result["conflicts"][0]["reason"].lower()


# -----------------------------------------------------------------------------
# 18. Gemini Provider Errors & Network Handling
# -----------------------------------------------------------------------------
def test_get_gemini_response_missing_api_key():
    """Test 18: Missing Gemini API key raises AIProviderConfigError."""
    with patch.object(type(settings), "effective_api_key", new=property(lambda self: None)):
        with pytest.raises(AIProviderConfigError, match="Gemini API key is missing"):
            get_gemini_response(prompt="Hello", api_key="")


def test_get_gemini_response_rate_limit():
    """Test 19: Gemini 429 raises AIRateLimitError when retries are exhausted."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "RESOURCE_EXHAUSTED: Rate limit exceeded"
    mock_resp.headers = {}
    mock_resp.json.return_value = {"error": {"message": "Rate limit exceeded"}}

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(AIRateLimitError, match="rate limit exceeded"):
            get_gemini_response(prompt="Hello", api_key="valid_key", max_retries=0)


def test_get_gemini_response_timeout():
    """Test 20: Network timeout raises AIProviderTimeoutError."""
    import httpx
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timeout")):
        with pytest.raises(AIProviderTimeoutError, match="timed out"):
            get_gemini_response(prompt="Hello", api_key="valid_key", max_retries=0)


# -----------------------------------------------------------------------------
# 21. Multiple Occurrences of Target Text
# -----------------------------------------------------------------------------
def test_multiple_occurrences_handled_non_overlapping():
    """Test 21: Multiple occurrences of the same phrase can each be replaced without conflict."""
    content = "fast performance and fast delivery"
    suggestions = [
        {
            "id": "s1",
            "original_text": "fast",
            "suggested_text": "lightning-fast",
            "status": "accepted",
        },
        {
            "id": "s2",
            "original_text": "fast",
            "suggested_text": "rapid",
            "status": "accepted",
        },
    ]

    result = apply_accepted_suggestions(content, suggestions)
    assert result["final_content"] == "lightning-fast performance and rapid delivery"
    assert len(result["applied_suggestions"]) == 2
    assert len(result["conflicts"]) == 0


# -----------------------------------------------------------------------------
# 22. End-to-End Lifecycle Simulation
# -----------------------------------------------------------------------------
def test_end_to_end_improvement_lifecycle():
    """Test 22: Simulates the entire interactive lifecycle from initial generation to final copy."""
    original = "Our tool is good. It makes reporting simple and fun."

    mock_response = json.dumps({
        "status": "success",
        "suggestions": [
            {
                "id": "suggestion_1",
                "original_text": "is good",
                "suggested_text": "delivers exceptional precision",
                "category": "Marketing Effectiveness",
                "explanation": "Enhances impact.",
                "status": "pending",
            },
            {
                "id": "suggestion_2",
                "original_text": "simple and fun",
                "suggested_text": "intuitive and engaging",
                "category": "Tone",
                "explanation": "More professional tone.",
                "status": "pending",
            },
        ],
    })

    with patch("app.user_improvements.get_gemini_response", return_value=mock_response):
        batch = generate_improvements(original, "Make it enterprise-ready.")

    suggestions = batch["suggestions"]
    assert len(suggestions) == 2

    # Step 1: User accepts suggestion 1
    accept_suggestion(suggestions, "suggestion_1")

    # Step 2: User custom-edits suggestion 2 then accepts it
    edit_suggestion(suggestions, "suggestion_2", "frictionless and highly productive")
    accept_suggestion(suggestions, "suggestion_2")

    # Step 3: Apply changes
    result = apply_accepted_suggestions(original, suggestions)
    expected = "Our tool delivers exceptional precision. It makes reporting frictionless and highly productive."
    assert result["final_content"] == expected
    assert len(result["applied_suggestions"]) == 2
    assert len(result["conflicts"]) == 0

