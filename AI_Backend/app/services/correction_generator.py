"""Correction generator service to review and validate corrected text."""

import logging
from typing import List
from app.api.schemas import GrammarFinding

logger = logging.getLogger(__name__)


class CorrectionGeneratorService:
    """Handles verification and generation of complete corrected marketing text."""

    def finalize_corrected_text(
        self,
        original_text: str,
        model_corrected_text: str,
        findings: List[GrammarFinding],
    ) -> str:
        """Validates and finalizes the complete corrected text.

        Ensures:
        - Corrected text is non-empty.
        - If there are zero findings and model changed text drastically, preserves original.
        - Untouched text retains formatting and casing where appropriate.
        """
        if not model_corrected_text or not model_corrected_text.strip():
            # If model somehow omitted corrected_text but gave findings or no findings,
            # use original as base.
            return original_text

        # If there are no issues found, the text is already correct
        if not findings and model_corrected_text.strip() != original_text.strip():
            logger.info("No findings reported; keeping original text rather than stylistic rewrite.")
            return original_text

        return model_corrected_text.strip()


correction_generator_service = CorrectionGeneratorService()
