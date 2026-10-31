"""Grammar and language analyzer service integrating LLM and structured schemas."""

import logging
from typing import Optional, List, Dict
from app.api.schemas import (
    GrammarFinding,
    AnalysisSummary,
    TextAnalysisResponse,
)
from app.prompts.grammar_analysis import (
    SYSTEM_PROMPT,
    build_analysis_prompt,
)
from app.services.ai_provider import AIProviderService, ai_provider_service
from app.services.correction_generator import (
    CorrectionGeneratorService,
    correction_generator_service,
)
from app.core.exceptions import AIProviderResponseError

logger = logging.getLogger(__name__)


class GrammarAnalyzerService:
    """Orchestrates language, grammar, spelling, and tone analysis."""

    def __init__(
        self,
        ai_provider: Optional[AIProviderService] = None,
        correction_generator: Optional[CorrectionGeneratorService] = None,
    ):
        self.ai_provider = ai_provider or ai_provider_service
        self.correction_generator = (
            correction_generator or correction_generator_service
        )

    def _locate_offsets(
        self, text: str, snippet: str, provided_start: Optional[int], provided_end: Optional[int]
    ) -> tuple[Optional[int], Optional[int]]:
        """Validates or calculates character offsets for the snippet in original text."""
        if provided_start is not None and provided_end is not None:
            if 0 <= provided_start < len(text) and provided_start < provided_end <= len(text):
                # Verify that snippet matches at these offsets
                if text[provided_start:provided_end] == snippet:
                    return provided_start, provided_end

        # If not provided or incorrect, search for exact match
        idx = text.find(snippet)
        if idx != -1:
            return idx, idx + len(snippet)

        # Case-insensitive search fallback
        lower_idx = text.lower().find(snippet.lower())
        if lower_idx != -1:
            return lower_idx, lower_idx + len(snippet)

        return None, None

    async def analyze(
        self,
        text: str,
        language: Optional[str] = "English",
        content_type: Optional[str] = None,
        target_audience: Optional[str] = None,
        instructions: Optional[str] = None,
        brand_context: Optional[str] = None,
    ) -> TextAnalysisResponse:
        """Executes full dynamic grammar analysis on the provided text."""
        prompt = build_analysis_prompt(
            text=text,
            language=language,
            content_type=content_type,
            target_audience=target_audience,
            instructions=instructions,
            brand_context=brand_context,
        )

        raw_data = await self.ai_provider.generate_structured_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        if not isinstance(raw_data, dict):
            raise AIProviderResponseError(
                "Model output is not a JSON object.",
                details={"raw_data": str(raw_data)[:200]},
            )

        raw_findings = raw_data.get("findings", [])
        if not isinstance(raw_findings, list):
            raw_findings = []

        validated_findings: List[GrammarFinding] = []
        findings_by_category: Dict[str, int] = {}
        findings_by_severity: Dict[str, int] = {}

        for idx, item in enumerate(raw_findings):
            if not isinstance(item, dict):
                continue

            finding_id = str(item.get("id") or f"finding_{idx + 1}")
            category = str(item.get("category") or "grammar").lower()
            severity = str(item.get("severity") or "medium").lower()
            if severity not in {"low", "medium", "high"}:
                severity = "medium"

            orig_snippet = str(item.get("original_text") or "").strip()
            suggestion = str(item.get("suggestion") or "").strip()
            explanation = str(item.get("explanation") or "").strip()

            confidence_raw = item.get("confidence")
            confidence: Optional[float] = None
            if confidence_raw is not None:
                try:
                    confidence = max(0.0, min(1.0, float(confidence_raw)))
                except (ValueError, TypeError):
                    confidence = None

            start_offset, end_offset = self._locate_offsets(
                text=text,
                snippet=orig_snippet,
                provided_start=item.get("start_offset"),
                provided_end=item.get("end_offset"),
            )

            finding = GrammarFinding(
                id=finding_id,
                category=category,
                severity=severity,
                original_text=orig_snippet,
                suggestion=suggestion,
                explanation=explanation,
                confidence=confidence,
                start_offset=start_offset,
                end_offset=end_offset,
            )
            validated_findings.append(finding)

            findings_by_category[category] = findings_by_category.get(category, 0) + 1
            findings_by_severity[severity] = findings_by_severity.get(severity, 0) + 1

        raw_corrected = str(raw_data.get("corrected_text") or "")
        final_corrected = self.correction_generator.finalize_corrected_text(
            original_text=text,
            model_corrected_text=raw_corrected,
            findings=validated_findings,
        )

        summary_data = raw_data.get("summary")
        assessment = ""
        if isinstance(summary_data, dict):
            assessment = str(summary_data.get("assessment") or "")
        elif isinstance(summary_data, str):
            assessment = summary_data

        if not assessment:
            if validated_findings:
                assessment = f"Detected {len(validated_findings)} language issues across {len(findings_by_category)} categories."
            else:
                assessment = "Text analyzed successfully. No grammatical, spelling, or stylistic errors found."

        summary = AnalysisSummary(
            total_findings=len(validated_findings),
            findings_by_category=findings_by_category,
            findings_by_severity=findings_by_severity,
            assessment=assessment,
        )

        return TextAnalysisResponse(
            original_text=text,
            findings=validated_findings,
            corrected_text=final_corrected,
            summary=summary,
        )


grammar_analyzer_service = GrammarAnalyzerService()
