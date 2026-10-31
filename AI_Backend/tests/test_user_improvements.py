"""Comprehensive Unit Tests for User-Driven Content Improvements Module.

Tests cover all 15 required scenarios:
1. Gemini suggestion generation.
2. Empty instructions.
3. Invalid Gemini response.
4. Accepting a suggestion.
5. Rejecting a suggestion.
6. Editing a suggestion.
7. Accepting all suggestions.
8. Applying accepted suggestions.
9. Ensuring rejected suggestions are not applied.
10. Ensuring pending suggestions are not applied.
11. Restoring original content.
12. Handling overlapping suggestions.
13. Handling suggestions that do not match the original text.
14. Regenerating suggestions.
15. Ensuring original content remains unchanged.

All tests strictly mock Gemini calls and do not consume API quota.
"""

import sys
import unittest
from pathlib import Path

# Ensure AI_Backend is in Python sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.user_improvements import (
    generate_improvements,
    accept_suggestion,
    reject_suggestion,
    edit_suggestion,
    accept_all_suggestions,
    restore_original,
    apply_accepted_suggestions,
    regenerate_improvements,
    build_user_prompt,
)


class TestUserDrivenContentImprovements(unittest.TestCase):
    """Test suite covering the 15 specification requirements for user_improvements."""

    def setUp(self):
        self.original_content = (
            "Our product helps people to manage their work and make things better."
        )
        self.mock_suggestions = [
            {
                "id": "suggestion_1",
                "original_text": "Our product helps people to manage their work",
                "suggested_text": "Our platform streamlines workflow management",
                "category": "Conciseness",
                "explanation": "The revised sentence is more concise and professional.",
                "status": "pending",
            },
            {
                "id": "suggestion_2",
                "original_text": "make things better",
                "suggested_text": "improve overall productivity",
                "category": "Professionalism",
                "explanation": "More specific business terminology.",
                "status": "pending",
            },
        ]
        self.context = {
            "content_type": "Marketing Copy",
            "target_audience": "Business Professionals",
            "language": "English",
            "brand_guidelines": ["Use active voice", "Be concise"],
            "preserved_entities": ["BrandProof AI"],
        }

    # -------------------------------------------------------------------------
    # 1. Gemini suggestion generation
    # -------------------------------------------------------------------------
    def test_gemini_suggestion_generation(self):
        """Test successful suggestion generation from structured Gemini response."""
        def mock_gemini(prompt, system_prompt):
            self.assertIn("BrandProof AI", prompt)
            self.assertIn("Business Professionals", prompt)
            return {
                "status": "success",
                "suggestions": [
                    {
                        "id": "suggestion_1",
                        "original_text": "helps people to manage their work",
                        "suggested_text": "streamlines workflow management",
                        "category": "Conciseness",
                        "explanation": "More direct phrasing.",
                        "status": "pending",
                    }
                ],
            }

        result = generate_improvements(
            original_content=self.original_content,
            user_instructions="Make it more concise.",
            existing_findings=[],
            context=self.context,
            gemini_client=mock_gemini,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["suggestions"]), 1)
        sugg = result["suggestions"][0]
        self.assertEqual(sugg["id"], "suggestion_1")
        self.assertEqual(sugg["original_text"], "helps people to manage their work")
        self.assertEqual(sugg["suggested_text"], "streamlines workflow management")
        self.assertEqual(sugg["category"], "Conciseness")
        self.assertEqual(sugg["status"], "pending")

    # -------------------------------------------------------------------------
    # 2. Empty instructions
    # -------------------------------------------------------------------------
    def test_empty_instructions(self):
        """Test validation error when user instructions are empty or whitespace."""
        called = False

        def mock_gemini(prompt, system_prompt):
            nonlocal called
            called = True
            return {}

        result_empty = generate_improvements(
            original_content=self.original_content,
            user_instructions="",
            gemini_client=mock_gemini,
        )
        self.assertEqual(result_empty["status"], "error")
        self.assertIn("User instructions cannot be empty", result_empty["message"])
        self.assertEqual(result_empty["suggestions"], [])
        self.assertFalse(called, "Gemini should not be called when instructions are empty.")

        result_whitespace = generate_improvements(
            original_content=self.original_content,
            user_instructions="    ",
            gemini_client=mock_gemini,
        )
        self.assertEqual(result_whitespace["status"], "error")
        self.assertFalse(called)

    # -------------------------------------------------------------------------
    # 3. Invalid Gemini response
    # -------------------------------------------------------------------------
    def test_invalid_gemini_response(self):
        """Test graceful error handling when Gemini returns invalid JSON or raises exception."""
        # Case A: Unparseable malformed JSON string
        def mock_broken_json(prompt, system_prompt):
            return "NOT_VALID_JSON {broken: true"

        result_broken = generate_improvements(
            original_content=self.original_content,
            user_instructions="Make it punchy.",
            gemini_client=mock_broken_json,
        )
        self.assertEqual(result_broken["status"], "error")
        self.assertIn("Malformed JSON", result_broken["message"])
        self.assertEqual(result_broken["suggestions"], [])

        # Case B: Gemini raises an exception (e.g. network failure)
        def mock_failing_gemini(prompt, system_prompt):
            raise RuntimeError("API connection timeout")

        result_exception = generate_improvements(
            original_content=self.original_content,
            user_instructions="Make it punchy.",
            gemini_client=mock_failing_gemini,
        )
        self.assertEqual(result_exception["status"], "error")
        self.assertIn("API connection timeout", result_exception["message"])
        self.assertEqual(result_exception["suggestions"], [])

    # -------------------------------------------------------------------------
    # 4. Accepting a suggestion
    # -------------------------------------------------------------------------
    def test_accept_suggestion(self):
        """Test marking a specific suggestion as accepted."""
        suggestions = [dict(s) for s in self.mock_suggestions]
        updated = accept_suggestion(suggestions, "suggestion_1")

        s1 = next(s for s in updated if s["id"] == "suggestion_1")
        s2 = next(s for s in updated if s["id"] == "suggestion_2")

        self.assertEqual(s1["status"], "accepted")
        self.assertEqual(s2["status"], "pending", "Other suggestions should remain unchanged.")

    # -------------------------------------------------------------------------
    # 5. Rejecting a suggestion
    # -------------------------------------------------------------------------
    def test_reject_suggestion(self):
        """Test marking a specific suggestion as rejected."""
        suggestions = [dict(s) for s in self.mock_suggestions]
        updated = reject_suggestion(suggestions, "suggestion_2")

        s1 = next(s for s in updated if s["id"] == "suggestion_1")
        s2 = next(s for s in updated if s["id"] == "suggestion_2")

        self.assertEqual(s1["status"], "pending", "Other suggestions should remain unchanged.")
        self.assertEqual(s2["status"], "rejected")

    # -------------------------------------------------------------------------
    # 6. Editing a suggestion
    # -------------------------------------------------------------------------
    def test_edit_suggestion(self):
        """Test user modifying the suggested text of a suggestion."""
        suggestions = [dict(s) for s in self.mock_suggestions]
        new_text = "Our solution optimizes workflow efficiency"
        updated = edit_suggestion(suggestions, "suggestion_1", new_text)

        s1 = next(s for s in updated if s["id"] == "suggestion_1")
        self.assertEqual(s1["suggested_text"], new_text)
        self.assertTrue(s1.get("is_edited"))

    # -------------------------------------------------------------------------
    # 7. Accepting all suggestions
    # -------------------------------------------------------------------------
    def test_accept_all_suggestions(self):
        """Test accepting all pending suggestions while preserving rejected ones."""
        suggestions = [
            {"id": "s1", "status": "pending", "original_text": "a", "suggested_text": "b"},
            {"id": "s2", "status": "rejected", "original_text": "c", "suggested_text": "d"},
            {"id": "s3", "status": "pending", "original_text": "e", "suggested_text": "f"},
        ]
        updated = accept_all_suggestions(suggestions)

        self.assertEqual(updated[0]["status"], "accepted")
        self.assertEqual(updated[1]["status"], "rejected", "Rejected suggestions must not be converted.")
        self.assertEqual(updated[2]["status"], "accepted")

    # -------------------------------------------------------------------------
    # 8. Applying accepted suggestions
    # -------------------------------------------------------------------------
    def test_apply_accepted_suggestions(self):
        """Test applying accepted suggestions to produce correct final content."""
        content = "Our product helps people to manage their work and make things better."
        suggestions = [
            {
                "id": "s1",
                "original_text": "helps people to manage their work",
                "suggested_text": "streamlines workflow management",
                "status": "accepted",
            },
            {
                "id": "s2",
                "original_text": "make things better",
                "suggested_text": "boosts team efficiency",
                "status": "accepted",
            },
        ]

        result = apply_accepted_suggestions(content, suggestions)

        expected_final = "Our product streamlines workflow management and boosts team efficiency."
        self.assertEqual(result["final_content"], expected_final)
        self.assertEqual(len(result["applied_suggestions"]), 2)
        self.assertEqual(result["conflicts"], [])

    # -------------------------------------------------------------------------
    # 9. Ensuring rejected suggestions are not applied
    # -------------------------------------------------------------------------
    def test_rejected_suggestions_not_applied(self):
        """Test that rejected suggestions are strictly excluded from final content."""
        content = "Alpha beta gamma."
        suggestions = [
            {
                "id": "s1",
                "original_text": "beta",
                "suggested_text": "delta",
                "status": "rejected",
            }
        ]

        result = apply_accepted_suggestions(content, suggestions)

        self.assertEqual(result["final_content"], content, "Rejected suggestions must never modify content.")
        self.assertEqual(result["applied_suggestions"], [])
        self.assertEqual(len(result["rejected_suggestions"]), 1)
        self.assertEqual(result["rejected_suggestions"][0]["id"], "s1")

    # -------------------------------------------------------------------------
    # 10. Ensuring pending suggestions are not applied
    # -------------------------------------------------------------------------
    def test_pending_suggestions_not_applied(self):
        """Test that pending suggestions are strictly excluded from final content."""
        content = "Alpha beta gamma."
        suggestions = [
            {
                "id": "s1",
                "original_text": "beta",
                "suggested_text": "delta",
                "status": "pending",
            }
        ]

        result = apply_accepted_suggestions(content, suggestions)

        self.assertEqual(result["final_content"], content, "Pending suggestions must never modify content.")
        self.assertEqual(result["applied_suggestions"], [])
        self.assertEqual(len(result["pending_suggestions"]), 1)
        self.assertEqual(result["pending_suggestions"][0]["id"], "s1")

    # -------------------------------------------------------------------------
    # 11. Restoring original content
    # -------------------------------------------------------------------------
    def test_restore_original(self):
        """Test restoring original content leaves it identical and unmodified."""
        content = "Original copy without any modifications."
        restored = restore_original(content)
        self.assertEqual(restored, content)
        self.assertIsInstance(restored, str)

    # -------------------------------------------------------------------------
    # 12. Handling overlapping suggestions
    # -------------------------------------------------------------------------
    def test_handling_overlapping_suggestions(self):
        """Test that overlapping suggestions are reported as conflicts and not corrupted."""
        content = "The quick brown fox jumps over the lazy dog."
        # s1: "quick brown fox" -> span [4, 19]
        # s2: "brown fox jumps" -> span [10, 25] (overlaps with s1)
        suggestions = [
            {
                "id": "s1",
                "original_text": "quick brown fox",
                "suggested_text": "speedy auburn fox",
                "status": "accepted",
            },
            {
                "id": "s2",
                "original_text": "brown fox jumps",
                "suggested_text": "fox leaps",
                "status": "accepted",
            },
        ]

        result = apply_accepted_suggestions(content, suggestions)

        # One suggestion should be safely applied, the conflicting one recorded in conflicts
        self.assertEqual(len(result["applied_suggestions"]), 1)
        self.assertEqual(result["applied_suggestions"][0]["id"], "s1")
        self.assertEqual(len(result["conflicts"]), 1)
        conflict = result["conflicts"][0]
        self.assertEqual(conflict["suggestion_id"], "s2")
        self.assertIn("Overlaps", conflict["reason"])
        self.assertEqual(result["final_content"], "The speedy auburn fox jumps over the lazy dog.")

    # -------------------------------------------------------------------------
    # 13. Handling suggestions that do not match the original text
    # -------------------------------------------------------------------------
    def test_suggestions_not_matching_original_text(self):
        """Test that suggestions with non-matching original_text report conflicts safely."""
        content = "Our platform is completely reliable."
        suggestions = [
            {
                "id": "s1",
                "original_text": "This text does not exist anywhere in the content",
                "suggested_text": "Replacement text",
                "status": "accepted",
            }
        ]

        result = apply_accepted_suggestions(content, suggestions)

        self.assertEqual(result["final_content"], content, "Non-matching suggestions must not corrupt text.")
        self.assertEqual(len(result["applied_suggestions"]), 0)
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(result["conflicts"][0]["suggestion_id"], "s1")
        self.assertIn("does not match", result["conflicts"][0]["reason"])

    # -------------------------------------------------------------------------
    # 14. Regenerating suggestions
    # -------------------------------------------------------------------------
    def test_regenerating_suggestions(self):
        """Test generating a fresh batch of suggestions with new instructions."""
        previous_suggestions = [
            {
                "id": "suggestion_1",
                "original_text": "helps people",
                "suggested_text": "empowers professionals",
                "status": "accepted",
            }
        ]

        def mock_regen_gemini(prompt, system_prompt):
            self.assertIn("PREVIOUS SUGGESTIONS", prompt)
            self.assertIn("empowers professionals", prompt)
            return {
                "status": "success",
                "suggestions": [
                    {
                        "id": "suggestion_1",  # duplicate ID from model
                        "original_text": "make things better",
                        "suggested_text": "accelerate growth",
                        "category": "Conciseness",
                        "explanation": "More action-oriented.",
                        "status": "pending",
                    }
                ],
            }

        result = regenerate_improvements(
            original_content=self.original_content,
            new_instructions="Now make it punchier and shorter.",
            previous_suggestions=previous_suggestions,
            gemini_client=mock_regen_gemini,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["suggestions"]), 1)
        fresh_sugg = result["suggestions"][0]
        # ID collision resolution ensures unique ID
        self.assertNotEqual(fresh_sugg["id"], "suggestion_1")
        self.assertIn("suggestion_1_regen_1", fresh_sugg["id"])
        self.assertEqual(fresh_sugg["status"], "pending")
        # Ensure previous_suggestions object was not mutated
        self.assertEqual(previous_suggestions[0]["id"], "suggestion_1")
        self.assertEqual(previous_suggestions[0]["status"], "accepted")

    # -------------------------------------------------------------------------
    # 15. Ensuring original content remains unchanged
    # -------------------------------------------------------------------------
    def test_original_content_remains_unchanged(self):
        """Test that apply_accepted_suggestions never mutates original content object."""
        content = "Immutable original text statement."
        original_copy = str(content)

        suggestions = [
            {
                "id": "s1",
                "original_text": "original text statement",
                "suggested_text": "revised formulation",
                "status": "accepted",
            }
        ]

        result = apply_accepted_suggestions(content, suggestions)

        # Content variable remains strictly identical
        self.assertEqual(content, original_copy)
        self.assertEqual(result["original_content"], original_copy)
        self.assertNotEqual(result["final_content"], original_copy)
        self.assertEqual(result["final_content"], "Immutable revised formulation.")


if __name__ == "__main__":
    unittest.main()
